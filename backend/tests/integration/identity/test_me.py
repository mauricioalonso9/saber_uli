"""T074: `GET /api/v1/me` (contrato: esquema `Me`; FR-014, FR-019, FR-022, FR-023, FR-038)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import CommittedLogin

ME_KEYS = {
    "id",
    "kind",
    "status",
    "display_name",
    "email",
    "roles",
    "permissions",
    "onboarding",
    "access",
}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def publish_policy(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[Callable[[], Awaitable[UUID]]]:
    created: list[UUID] = []

    async def publish() -> UUID:
        async with app_engine.begin() as conn:
            version = (
                await conn.execute(
                    text(
                        """INSERT INTO identity.policy_versions (version, title, body_markdown,
                               effective_from) VALUES (:v, 'Política', '...', now()) RETURNING id"""
                    ),
                    {"v": f"me-{uuid4()}"},
                )
            ).scalar_one()
        created.append(version)
        return UUID(str(version))

    yield publish
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM identity.consents WHERE policy_version_id = ANY(:ids)"),
            {"ids": created},
        )
        await conn.execute(
            text("DELETE FROM identity.policy_versions WHERE id = ANY(:ids)"), {"ids": created}
        )
    await engine.dispose()


async def get_me(client: httpx.AsyncClient, token: str) -> dict[str, Any]:
    response = await client.get("/api/v1/me", headers=bearer(token))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_campos_del_esquema_me_para_un_estudiante_nuevo(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    user, token = await committed_login()

    me = await get_me(api_client, token)

    assert set(me) >= ME_KEYS
    assert me["id"] == str(user.id)
    assert (me["kind"], me["status"]) == ("institutional", "active")
    assert (me["display_name"], me["email"]) == (user.display_name, user.email)
    assert me["roles"] == ["student"]
    assert me["permissions"] == []
    # Sin autorización de datos y sin perfil: /me responde igual (ruta exenta, FR-014).
    assert me["onboarding"]["consent_required"] is True
    assert me["onboarding"]["profile_required"] is True
    assert me["access"]["valid"] is True
    assert me["access"]["privileged_session"] is False


async def test_el_plazo_sin_conexion_es_validated_at_mas_7_dias(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()

    access = (await get_me(api_client, token))["access"]

    validated = datetime.fromisoformat(access["validated_at"])
    grace = datetime.fromisoformat(access["offline_grace_until"])
    assert grace - validated == timedelta(days=7)
    assert validated.tzinfo is not None


async def test_permisos_segun_roles(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login(Role.TEACHER, Role.PROGRAM_DIRECTOR)

    me = await get_me(api_client, token)

    assert me["roles"] == ["program_director", "student", "teacher"]
    assert me["permissions"] == [
        "groups:read_own_students",
        "invitations:manage_own",
        "programs:read_aggregated",
    ]


async def test_sesion_privilegiada(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login(Role.ADMIN, priv=True)

    assert (await get_me(api_client, token))["access"]["privileged_session"] is True


async def test_con_autorizacion_vigente_y_perfil_completo(
    api_client: httpx.AsyncClient,
    committed_login: CommittedLogin,
    publish_policy: Callable[[], Awaitable[UUID]],
    app_engine: AsyncEngine,
) -> None:
    user, token = await committed_login()
    version = await publish_policy()
    async with app_engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
                   VALUES (:u, :p, 'accepted', 'web_pwa')"""
            ),
            {"u": user.id, "p": version},
        )
        await conn.execute(
            text("UPDATE identity.users SET onboarding_completed_at = now() WHERE id = :u"),
            {"u": user.id},
        )

    onboarding = (await get_me(api_client, token))["onboarding"]

    assert onboarding == {
        "consent_required": False,
        "current_policy_version_id": str(version),
        "profile_required": False,
    }


async def test_invitado_con_vencimiento_de_acceso(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    inviter, _ = await committed_login(Role.TEACHER)
    guest, token = await committed_login(guest=True)
    async with app_engine.begin() as conn:
        expires = (
            await conn.execute(
                text(
                    """INSERT INTO identity.invitations
                           (invited_by, guest_user_id, status, access_expires_at, created_at)
                       VALUES (:by, :g, 'accepted', now() + interval '30 days',
                               now() - interval '1 day')
                       RETURNING access_expires_at"""
                ),
                {"by": inviter.id, "g": guest.id},
            )
        ).scalar_one()

    me = await get_me(api_client, token)

    assert (me["kind"], me["status"], me["roles"]) == ("guest", "active", ["guest"])
    assert datetime.fromisoformat(me["access"]["guest_access_expires_at"]) == expires


async def test_sin_token(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/me")

    assert response.status_code == 401
