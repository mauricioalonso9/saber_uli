"""T108: un invitado pide un enlace de ingreso (FR-013; research R-18, R-19, R-31).

`POST /api/auth/guest/link-requests` responde siempre 202 con el mismo cuerpo, exista o no el
correo. Solo un invitado con acceso vigente genera `identity.SignInLinkRequested`, cuyo payload
lleva solo el id de la invitación (el token lo genera el worker).
"""

import io
from uuid import UUID

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import text

from saber_uli.identity.domain.roles import Role
from saber_uli.main import create_app
from tests.integration.conftest import CommittedLogin, settings_for
from tests.integration.identity.guests import Guests

REQUESTS = "/api/auth/guest/link-requests"
EVENT = "identity.SignInLinkRequested"


@pytest.fixture
async def teacher(committed_login: CommittedLogin) -> UUID:
    user, _ = await committed_login(Role.TEACHER)
    assert user.id is not None
    return user.id


async def request_link(client: httpx.AsyncClient, email: str) -> httpx.Response:
    return await client.post(REQUESTS, json={"email": email})


async def make_active_guest(
    client: httpx.AsyncClient, guests: Guests, teacher: UUID, **options: object
) -> tuple[UUID, str]:
    invitation_id, email = await guests.invitation(teacher, **options)  # type: ignore[arg-type]
    token = await guests.link(invitation_id)
    response = await client.post("/api/auth/guest/sessions", json={"token": token})
    assert response.status_code == 200, response.text
    return invitation_id, email


async def test_un_invitado_vigente_genera_el_evento_sin_correo_ni_token(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> None:
    invitation_id, email = await make_active_guest(api_client, guests, teacher)

    response = await request_link(api_client, email.upper())  # sin distinguir mayúsculas

    assert response.status_code == 202
    events = await guests.outbox_events(invitation_id)
    sign_in = [(kind, payload) for kind, payload in events if kind == EVENT]
    assert sign_in == [(EVENT, {"invitation_id": str(invitation_id)})]
    assert email.lower() not in str(events).lower()


async def test_la_respuesta_es_identica_exista_o_no_el_correo(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> None:
    _, email = await make_active_guest(api_client, guests, teacher)

    known = await request_link(api_client, email)
    unknown = await request_link(api_client, guests.new_email())

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert set(known.json()) == {"message"}
    assert known.headers["content-type"] == unknown.headers["content-type"]


@pytest.mark.parametrize("case", ["pendiente", "vencido", "revocado"])
async def test_sin_acceso_vigente_no_se_genera_el_evento(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID, case: str
) -> None:
    if case == "pendiente":
        invitation_id, email = await guests.invitation(teacher)
    else:
        invitation_id, email = await make_active_guest(api_client, guests, teacher)
        async with guests.engine.begin() as conn:
            statement = (
                "UPDATE identity.invitations SET access_expires_at = now() - interval '1 second',"
                " created_at = now() - interval '2 days' WHERE id = :id"
                if case == "vencido"
                else "UPDATE identity.invitations SET status = 'revoked', revoked_at = now()"
                " WHERE id = :id"
            )
            await conn.execute(text(statement), {"id": invitation_id})

    response = await request_link(api_client, email)

    assert response.status_code == 202
    assert [kind for kind, _ in await guests.outbox_events(invitation_id) if kind == EVENT] == []


async def test_un_correo_invalido_responde_422(api_client: httpx.AsyncClient) -> None:
    response = await request_link(api_client, "no-es-un-correo")

    assert response.status_code == 422


def client_from(app: object, ip: str) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(ip, 40000))  # type: ignore[arg-type]
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_limite_de_5_por_hora_por_correo_aunque_cambie_la_ip(
    migrated_database: dict[str, str], redis_url: str, redis_client: Redis, guests: Guests
) -> None:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    email = guests.new_email()
    statuses = []
    for attempt in range(6):
        async with client_from(app, f"198.51.100.{attempt + 1}") as client:
            statuses.append((await request_link(client, email)).status_code)

    assert statuses == [202] * 5 + [429]


async def test_limite_de_20_por_hora_por_ip(
    migrated_database: dict[str, str], redis_url: str, redis_client: Redis, guests: Guests
) -> None:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    statuses = []
    async with client_from(app, "198.51.100.200") as client:
        for _ in range(21):
            statuses.append((await request_link(client, guests.new_email())).status_code)

    assert statuses[:20] == [202] * 20
    assert statuses[20] == 429
