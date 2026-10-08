"""T178b: ver las sesiones activas y cerrarlas (FR-037a, escenario 1.5; ASVS 4.0.3 V3.3.4).

`GET /api/v1/me/sessions`, `POST /api/v1/me/sessions/{sessionId}/revocation` y
`POST /api/v1/me/sessions/revocation` (todas menos la actual). Una sesión cerrada deja de servir
en su siguiente petición: su token de acceso ya emitido (lista de revocadas en Redis) y su token
de renovación.
"""

import io
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.api.auth_router import REFRESH_COOKIE
from saber_uli.identity.application.sessions import IssuedSession
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import AuthMethod
from saber_uli.identity.infrastructure.tokens import AccessTokenCodec
from saber_uli.main import create_app
from tests.integration.conftest import TEST_JWT_KEY, TEST_JWT_KID, CommittedLogin, settings_for

SESSIONS = "/api/v1/me/sessions"
XRW = {"X-Requested-With": "saber-uli"}
CODEC = AccessTokenCodec({TEST_JWT_KID: TEST_JWT_KEY}, active_kid=TEST_JWT_KID)


@pytest.fixture
def app(migrated_database: dict[str, str], redis_url: str, redis_client: Redis) -> FastAPI:
    return create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def open_session(app: FastAPI, user_id: UUID) -> IssuedSession:
    issued: IssuedSession = await app.state.session_service.open_session(
        user_id, AuthMethod.ENTRA_ID
    )
    return issued


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def session_ids(client: httpx.AsyncClient, token: str) -> list[tuple[str, bool]]:
    response = await client.get(SESSIONS, headers=bearer(token))
    assert response.status_code == 200, response.text
    return [(item["id"], item["current"]) for item in response.json()["items"]]


def sid(token: str) -> str:
    return str(CODEC.decode(token, now=datetime.now(UTC)).sid)


async def test_lista_solo_las_sesiones_activas_y_marca_la_actual(
    app: FastAPI,
    client: httpx.AsyncClient,
    committed_login: CommittedLogin,
    app_engine: AsyncEngine,
) -> None:
    user, token = await committed_login(Role.STUDENT)
    assert user.id is not None
    other = await open_session(app, user.id)
    idle = await open_session(app, user.id)
    closed = await open_session(app, user.id)
    async with app_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE identity.sessions SET last_seen_at = now() - interval '8 days'"
                " WHERE id = :id"
            ),
            {"id": sid(idle.access_token)},
        )
    await client.post(
        "/api/auth/logout", headers={**XRW, "Cookie": f"{REFRESH_COOKIE}={closed.refresh_token}"}
    )

    response = await client.get(SESSIONS, headers=bearer(token))

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert {(i["id"], i["current"]) for i in items} == {
        (sid(token), True),
        (sid(other.access_token), False),
    }
    assert all(i["auth_method"] == "entra_id" for i in items)
    assert all(
        set(i) == {"id", "auth_method", "started_at", "last_activity_at", "current"} for i in items
    )


async def test_cerrar_otra_sesion_la_corta_en_su_siguiente_peticion(
    app: FastAPI, client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    user, token = await committed_login(Role.STUDENT)
    assert user.id is not None
    other = await open_session(app, user.id)

    response = await client.post(
        f"{SESSIONS}/{sid(other.access_token)}/revocation", headers=bearer(token)
    )

    assert response.status_code == 204, response.text
    assert (await client.get("/api/v1/me", headers=bearer(other.access_token))).status_code == 401
    refresh = await client.post(
        "/api/auth/refresh", headers={**XRW, "Cookie": f"{REFRESH_COOKIE}={other.refresh_token}"}
    )
    assert refresh.status_code == 401
    assert (await client.get("/api/v1/me", headers=bearer(token))).status_code == 200
    assert await session_ids(client, token) == [(sid(token), True)]


async def test_una_sesion_ajena_o_inexistente_responde_404(
    app: FastAPI, client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login(Role.STUDENT)
    _, stranger_token = await committed_login(Role.STUDENT)

    for target in (sid(stranger_token), str(uuid4())):
        response = await client.post(f"{SESSIONS}/{target}/revocation", headers=bearer(token))
        assert response.status_code == 404, response.text

    assert (await client.get("/api/v1/me", headers=bearer(stranger_token))).status_code == 200


async def test_cerrar_todas_las_demas_conserva_la_actual(
    app: FastAPI, client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    user, token = await committed_login(Role.STUDENT)
    assert user.id is not None
    others = [await open_session(app, user.id) for _ in range(2)]

    response = await client.post(f"{SESSIONS}/revocation", headers=bearer(token))

    assert response.status_code == 204, response.text
    assert await session_ids(client, token) == [(sid(token), True)]
    for other in others:
        me = await client.get("/api/v1/me", headers=bearer(other.access_token))
        assert me.status_code == 401


async def test_sin_sesion_responde_401(client: httpx.AsyncClient) -> None:
    assert (await client.get(SESSIONS)).status_code == 401
    assert (await client.post(f"{SESSIONS}/revocation")).status_code == 401
