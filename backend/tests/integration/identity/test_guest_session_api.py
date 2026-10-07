"""T107: ingreso del invitado con el enlace del correo (FR-007, FR-011; escenarios 4.1, 4.3 y
4.4; research R-18).

`POST /api/auth/guest/sessions` consume el enlace (un solo uso), crea la cuenta del invitado al
aceptar la invitación, abre la sesión y fija la cookie `su_refresh`.
"""

import io
from typing import Any
from uuid import UUID

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from saber_uli.main import create_app
from tests.integration.conftest import CommittedLogin, settings_for
from tests.integration.identity.guests import Guests

SESSIONS = "/api/auth/guest/sessions"


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


@pytest.fixture
async def teacher(committed_login: CommittedLogin) -> UUID:
    user, _ = await committed_login(Role.TEACHER)
    assert user.id is not None
    return user.id


async def sign_in(client: httpx.AsyncClient, token: str) -> httpx.Response:
    return await client.post(SESSIONS, json={"token": token})


async def test_el_enlace_de_invitacion_crea_al_invitado_y_abre_la_sesion(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID, app_engine: AsyncEngine
) -> None:
    invitation_id, email = await guests.invitation(teacher)
    token = await guests.link(invitation_id)

    response = await sign_in(api_client, token)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 600
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("su_refresh=")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Path=/api/auth" in cookie
    assert await guests.link_used(token)

    me = await api_client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert (me.json()["kind"], me.json()["roles"], me.json()["email"]) == (
        "guest",
        ["guest"],
        email,
    )
    async with app_engine.connect() as conn:
        invitation = (
            await conn.execute(
                text(
                    "SELECT status, guest_user_id, accepted_at FROM identity.invitations"
                    " WHERE id = :id"
                ),
                {"id": invitation_id},
            )
        ).one()
        method = (
            await conn.execute(
                text("SELECT auth_method FROM identity.sessions WHERE user_id = :u"),
                {"u": invitation.guest_user_id},
            )
        ).scalar_one()
        actions = set(
            (
                await conn.execute(
                    text("SELECT action FROM identity.audit_events WHERE subject_user_id = :u"),
                    {"u": invitation.guest_user_id},
                )
            ).scalars()
        )
    assert invitation.status == "accepted"
    assert str(invitation.guest_user_id) == me.json()["id"]
    assert invitation.accepted_at is not None
    assert method == "guest_link"
    assert actions >= {"user.created", "invitation.accepted"}


async def test_un_enlace_usado_no_sirve_otra_vez(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> None:
    invitation_id, _ = await guests.invitation(teacher)
    token = await guests.link(invitation_id)
    assert (await sign_in(api_client, token)).status_code == 200

    again = await sign_in(api_client, token)

    assert again.status_code == 400
    assert problem_type(again) == "access-link-invalid"
    assert "set-cookie" not in again.headers


@pytest.mark.parametrize("case", ["vencido", "usado", "desconocido"])
async def test_enlaces_invalidos_responden_400(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID, case: str
) -> None:
    invitation_id, email = await guests.invitation(teacher)
    if case == "vencido":
        token = await guests.link(invitation_id, minutes=-1)
    elif case == "usado":
        token = await guests.link(invitation_id, used=True)
    else:
        token = "x" * 43

    response = await sign_in(api_client, token)

    assert response.status_code == 400
    assert problem_type(response) == "access-link-invalid"
    assert await guests.guest_user_id(email) is None


async def test_el_enlace_de_ingreso_entra_con_la_cuenta_existente(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> None:
    invitation_id, email = await guests.invitation(teacher)
    assert (await sign_in(api_client, await guests.link(invitation_id))).status_code == 200
    guest_id = await guests.guest_user_id(email)
    token = await guests.link(invitation_id, purpose="sign_in", minutes=15)

    response = await sign_in(api_client, token)

    assert response.status_code == 200, response.text
    assert await guests.guest_user_id(email) == guest_id


async def test_acceso_vencido_responde_403_y_no_crea_la_cuenta(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> None:
    invitation_id, email = await guests.invitation(teacher, access_days=-1)
    token = await guests.link(invitation_id)

    response = await sign_in(api_client, token)

    assert response.status_code == 403
    assert problem_type(response) == "guest-access-expired"
    assert await guests.guest_user_id(email) is None


async def test_acceso_revocado_responde_403(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> None:
    invitation_id, email = await guests.invitation(teacher)
    assert (await sign_in(api_client, await guests.link(invitation_id))).status_code == 200
    guest_id = await guests.guest_user_id(email)
    async with guests.engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE identity.invitations SET status = 'revoked', revoked_at = now()"
                " WHERE id = :id"
            ),
            {"id": invitation_id},
        )
    token = await guests.link(invitation_id, purpose="sign_in", minutes=15)

    response = await sign_in(api_client, token)

    assert response.status_code == 403
    assert problem_type(response) == "guest-access-revoked"
    assert guest_id is not None


async def test_un_token_mal_formado_responde_422(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(SESSIONS, json={"token": "corto"})

    assert response.status_code == 422


async def test_limite_de_10_por_minuto_por_ip(
    migrated_database: dict[str, str], redis_url: str, redis_client: Redis
) -> None:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    transport = httpx.ASGITransport(app=app, client=("203.0.113.7", 40000))
    statuses: list[Any] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(11):
            statuses.append((await sign_in(client, "y" * 43)).status_code)

    assert statuses[:10] == [400] * 10
    assert statuses[10] == 429
