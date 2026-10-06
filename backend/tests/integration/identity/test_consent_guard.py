"""T051: guardia de autorización de datos (FR-014; contrato: `x-consent-exempt`)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

import httpx
import pytest
import yaml
from fastapi import APIRouter, Depends, FastAPI
from redis.asyncio import Redis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.application.access_guard import AccessGuard
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.queries.consent_status import ConsentStatusQuery
from saber_uli.identity.infrastructure.epoch_cache import RedisEpochStore
from saber_uli.identity.infrastructure.tokens import AccessTokenCodec
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.api.auth import current_user
from saber_uli.shared.api.consent_guard import CONSENT_EXEMPT_OPERATIONS, require_consent
from saber_uli.shared.api.problems import install_problem_handlers
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import REPO, CommittedLogin

CONTRACT = REPO / "specs" / "001-identidad-acceso" / "contracts" / "openapi.yaml"


def test_la_lista_de_exentas_coincide_con_el_contrato() -> None:
    spec: dict[str, Any] = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    exempt = {
        op["operationId"]
        for operations in spec["paths"].values()
        for op in operations.values()
        if isinstance(op, dict) and op.get("x-consent-exempt")
    }

    assert exempt == CONSENT_EXEMPT_OPERATIONS


def build_app(app_engine: AsyncEngine, redis_url: str, token_codec: AccessTokenCodec) -> FastAPI:
    factory = create_session_factory(app_engine)

    def uow() -> SqlAlchemyIdentityUnitOfWork:
        return SqlAlchemyIdentityUnitOfWork(factory, EventBus())

    app = FastAPI()
    install_problem_handlers(app)
    app.state.authenticator = AccessGuard(
        decoder=token_codec, epochs=RedisEpochStore(redis_url), uow_factory=uow, clock=SystemClock()
    )
    app.state.consent_checker = ConsentStatusQuery(uow_factory=uow, clock=SystemClock())

    v1 = APIRouter(prefix="/api/v1", dependencies=[Depends(require_consent)])

    @v1.get("/me", operation_id="getMe")
    async def me(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> dict[str, str]:
        return {"id": str(user.id)}

    @v1.get("/me/profile", operation_id="getMyProfile")
    async def profile(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> dict[str, str]:
        return {"id": str(user.id)}

    app.include_router(v1)
    return app


Decide = Callable[[UUID, UUID, str], Awaitable[None]]


@pytest.fixture
async def policies(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[Callable[[timedelta], Awaitable[UUID]]]:
    created: list[UUID] = []

    async def publish(age: timedelta) -> UUID:
        async with app_engine.begin() as conn:
            version_id = (
                await conn.execute(
                    text(
                        """INSERT INTO identity.policy_versions
                               (version, title, body_markdown, effective_from)
                           VALUES (:v, 'Política', '...', :f) RETURNING id"""
                    ),
                    {"v": f"t-{uuid4()}", "f": datetime.now(UTC) - age},
                )
            ).scalar_one()
        created.append(version_id)
        return UUID(str(version_id))

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


async def decide(engine: AsyncEngine, user_id: UUID, version: UUID, decision: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel,
                       decided_at)
                   VALUES (:u, :p, :d, 'web_pwa', clock_timestamp())"""
            ),
            {"u": user_id, "p": version, "d": decision},
        )


@pytest.fixture
def app(
    app_engine: AsyncEngine, redis_url: str, redis_client: Redis, token_codec: AccessTokenCodec
) -> FastAPI:
    return build_app(app_engine, redis_url, token_codec)


async def get(app: FastAPI, path: str, token: str | None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as http:
        return await http.get(path, headers=headers)


def consent_required(response: httpx.Response) -> bool:
    return (
        response.status_code == 403
        and response.json()["type"] == "urn:saber-uli:problem:consent-required"
    )


async def test_sin_autorizacion_solo_responden_las_rutas_exentas(
    app: FastAPI, committed_login: CommittedLogin, policies: Any
) -> None:
    await policies(timedelta(days=1))
    _, token = await committed_login()

    assert (await get(app, "/api/v1/me", token)).status_code == 200
    assert consent_required(await get(app, "/api/v1/me/profile", token))


async def test_con_autorizacion_vigente_responde(
    app: FastAPI, committed_login: CommittedLogin, policies: Any, app_engine: AsyncEngine
) -> None:
    version = await policies(timedelta(days=1))
    user, token = await committed_login()
    await decide(app_engine, user.id, version, "accepted")

    assert (await get(app, "/api/v1/me/profile", token)).status_code == 200


async def test_revocar_suspende_el_acceso(
    app: FastAPI, committed_login: CommittedLogin, policies: Any, app_engine: AsyncEngine
) -> None:
    version = await policies(timedelta(days=1))
    user, token = await committed_login()
    await decide(app_engine, user.id, version, "accepted")
    await decide(app_engine, user.id, version, "revoked")

    assert consent_required(await get(app, "/api/v1/me/profile", token))


async def test_una_version_nueva_exige_aceptarla(
    app: FastAPI, committed_login: CommittedLogin, policies: Any, app_engine: AsyncEngine
) -> None:
    old = await policies(timedelta(days=30))
    user, token = await committed_login()
    await decide(app_engine, user.id, old, "accepted")
    await policies(timedelta(minutes=1))

    assert consent_required(await get(app, "/api/v1/me/profile", token))


async def test_sin_token_responde_401_antes_que_403(app: FastAPI) -> None:
    response = await get(app, "/api/v1/me/profile", None)

    assert response.status_code == 401
