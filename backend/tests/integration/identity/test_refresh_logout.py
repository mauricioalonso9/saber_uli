"""T049: renovación y cierre de sesión (research R-14, R-15, R-16; escenario 1.4; FR-037, FR-038).

PostgreSQL y Redis reales; reloj fijo para probar la inactividad. Los datos se confirman y se
limpian con `saber_migrator`.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from typing import Annotated, Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from saber_uli.identity.api.auth_router import REFRESH_COOKIE, router
from saber_uli.identity.application.access_guard import AccessGuard
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.sessions import SessionService
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import REUSE_GRACE, AuthMethod
from saber_uli.identity.domain.user import InstitutionalIdentity, User
from saber_uli.identity.infrastructure.epoch_cache import RedisEpochStore
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.identity.infrastructure.session_revocations import RedisSessionRevocations
from saber_uli.identity.infrastructure.tokens import AccessTokenCodec, RefreshTokenFactory
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.api.auth import current_user
from saber_uli.shared.api.problems import install_problem_handlers
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.infrastructure.db import create_session_factory
from saber_uli.shared.infrastructure.rate_limit import RateLimiter
from tests.integration.conftest import TEST_JWT_KEY, TEST_JWT_KID

T0 = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
CODEC = AccessTokenCodec({TEST_JWT_KID: TEST_JWT_KEY}, active_kid=TEST_JWT_KID)
XRW = {"X-Requested-With": "saber-uli"}


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


@pytest.fixture
def revocations(redis_url: str) -> RedisSessionRevocations:
    return RedisSessionRevocations(redis_url)


@pytest.fixture
def service(
    app_engine: AsyncEngine, clock: FixedClock, revocations: RedisSessionRevocations
) -> SessionService:
    factory = create_session_factory(app_engine)
    return SessionService(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus()),
        clock=clock,
        access_tokens=CODEC,
        refresh_tokens=RefreshTokenFactory(),
        revocations=revocations,
    )


@pytest.fixture
def app(
    service: SessionService,
    redis_url: str,
    redis_client: Redis,
    app_engine: AsyncEngine,
    clock: FixedClock,
    revocations: RedisSessionRevocations,
) -> FastAPI:
    application = FastAPI()
    install_problem_handlers(application)
    factory = create_session_factory(app_engine)
    application.state.session_service = service
    application.state.rate_limiter = RateLimiter(redis_url, hash_key=b"h" * 32)
    application.state.authenticator = AccessGuard(
        decoder=CODEC,
        epochs=RedisEpochStore(redis_url),
        revocations=revocations,
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus()),
        clock=clock,
    )
    application.include_router(router)

    @application.get("/api/v1/protegido")
    async def protected(
        user: Annotated[AuthenticatedUser, Depends(current_user)],
    ) -> dict[str, str]:
        return {"id": str(user.id)}

    return application


Login = Callable[..., Awaitable[tuple[User, str]]]


@pytest.fixture
async def login(
    app_engine: AsyncEngine, service: SessionService, migrated_database: dict[str, str]
) -> AsyncIterator[Login]:
    """Crea y confirma un usuario, abre su sesión y devuelve el token de renovación en claro."""
    created: list[UUID] = []

    async def create(*roles: Role, guest: bool = False) -> tuple[User, str]:
        async with AsyncSession(app_engine, expire_on_commit=False) as db:
            if guest:
                user = User.new_guest(email=f"g-{uuid4()}@correo.co", display_name=None, now=T0)
            else:
                user = User.new_institutional(
                    InstitutionalIdentity(tenant_id=TENANT, object_id=uuid4()),
                    email=f"p-{uuid4()}@unilibre.edu.co",
                    display_name="Persona",
                    now=T0,
                )
                for role in roles:
                    user.grant_role(role)
            await SqlAlchemyUserRepository(db).add(user)
            await db.commit()
        assert user.id is not None
        created.append(user.id)
        issued = await service.open_session(user.id, AuthMethod.ENTRA_ID)
        return user, issued.refresh_token

    yield create
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM identity.invitations WHERE guest_user_id = ANY(:ids)"),
            {"ids": created},
        )
        await conn.execute(
            text("DELETE FROM identity.audit_events WHERE subject_user_id = ANY(:ids)"),
            {"ids": created},
        )
        await conn.execute(
            text("DELETE FROM identity.users WHERE id = ANY(:ids)"), {"ids": created}
        )
    await engine.dispose()


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("203.0.113.7", 50000)),
        base_url="https://test",
    )


async def refresh(
    app: FastAPI, cookie: str | None, headers: dict[str, str] = XRW
) -> httpx.Response:
    cookies = {"Cookie": f"{REFRESH_COOKIE}={cookie}"} if cookie else {}
    async with client(app) as http:
        return await http.post("/api/auth/refresh", headers={**headers, **cookies})


def set_cookie(response: httpx.Response) -> Any:
    parsed: SimpleCookie = SimpleCookie()
    parsed.load(response.headers["set-cookie"])
    return parsed[REFRESH_COOKIE]


def problem(response: httpx.Response) -> str:
    assert response.status_code == 401, response.text
    return str(response.json()["type"]).removeprefix("urn:saber-uli:problem:")


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement), params)


# --- Renovación --------------------------------------------------------------------------------


async def test_exige_x_requested_with(app: FastAPI, login: Login) -> None:
    _, cookie = await login()

    response = await refresh(app, cookie, headers={})

    assert problem(response) == "unauthenticated"
    # El token no se consumió: con la cabecera sigue funcionando.
    assert (await refresh(app, cookie)).status_code == 200


async def test_renueva_rota_la_cookie_y_entrega_el_token(
    app: FastAPI, login: Login, clock: FixedClock
) -> None:
    user, cookie = await login(Role.ADMIN)
    clock.advance(timedelta(minutes=5))

    response = await refresh(app, cookie)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 600
    claims = CODEC.decode(body["access_token"], now=clock.now())
    assert claims.sub == user.id
    assert claims.roles == ("admin", "student")
    assert claims.priv is True  # autenticado hace 5 minutos (R-15)

    new = set_cookie(response)
    assert new.value != cookie
    assert new["httponly"] is True
    assert new["secure"] is True
    assert new["samesite"] == "Strict"
    assert new["path"] == "/api/auth"
    assert int(new["max-age"]) == int(timedelta(days=7).total_seconds())


async def test_dentro_del_margen_reutilizar_es_una_carrera_y_no_revoca(
    app: FastAPI, login: Login, clock: FixedClock
) -> None:
    # Dos pestañas que renuevan a la vez, o la app cerrada antes de recibir la cookie nueva.
    _, cookie = await login()
    first = await refresh(app, cookie)
    clock.advance(timedelta(seconds=5))

    second = await refresh(app, cookie)

    assert second.status_code == 200, second.text
    assert set_cookie(second).value != set_cookie(first).value
    assert (await refresh(app, set_cookie(first).value)).status_code == 200
    assert (await refresh(app, set_cookie(second).value)).status_code == 200


async def test_reutilizar_un_token_rotado_revoca_la_familia(
    app: FastAPI, login: Login, app_engine: AsyncEngine, clock: FixedClock
) -> None:
    user, cookie = await login()
    rotated = set_cookie(await refresh(app, cookie)).value
    clock.advance(REUSE_GRACE + timedelta(seconds=1))

    reused = await refresh(app, cookie)

    assert problem(reused) == "session-revoked"
    assert set_cookie(reused)["max-age"] == "0"
    # El token más reciente de la familia también quedó inválido.
    assert problem(await refresh(app, rotated)) == "session-revoked"
    # La reutilización queda auditada (sin datos personales).
    async with app_engine.connect() as conn:
        actions = (
            await conn.execute(
                text("SELECT action FROM identity.audit_events WHERE subject_user_id = :u"),
                {"u": user.id},
            )
        ).scalars()
        assert list(actions) == ["session.reuse_detected"]


async def test_cuenta_desactivada(app: FastAPI, login: Login, app_engine: AsyncEngine) -> None:
    user, cookie = await login()
    await sql(app_engine, "UPDATE identity.users SET status = 'disabled' WHERE id = :u", u=user.id)

    assert problem(await refresh(app, cookie)) == "account-disabled"


async def test_acceso_de_invitado_vencido(
    app: FastAPI, login: Login, app_engine: AsyncEngine
) -> None:
    inviter, _ = await login(Role.TEACHER)
    guest, cookie = await login(guest=True)
    await sql(
        app_engine,
        """INSERT INTO identity.invitations
               (invited_by, guest_user_id, status, access_expires_at, created_at)
           VALUES (:by, :g, 'accepted', :exp, :created)""",
        by=inviter.id,
        g=guest.id,
        exp=T0 - timedelta(minutes=1),
        created=T0 - timedelta(days=90),
    )

    assert problem(await refresh(app, cookie)) == "guest-access-expired"


async def test_inactividad_de_mas_de_7_dias(app: FastAPI, login: Login, clock: FixedClock) -> None:
    _, cookie = await login()
    clock.advance(timedelta(days=7, seconds=1))

    assert problem(await refresh(app, cookie)) == "session-expired"


async def test_sin_cookie_o_con_una_desconocida(app: FastAPI) -> None:
    assert problem(await refresh(app, None)) == "session-expired"
    assert problem(await refresh(app, "token-inventado")) == "session-expired"


async def test_renovar_cuenta_como_ingreso_para_la_conservacion(
    app: FastAPI, login: Login, clock: FixedClock, app_engine: AsyncEngine
) -> None:
    user, cookie = await login()
    clock.advance(timedelta(days=2))

    assert (await refresh(app, cookie)).status_code == 200
    async with app_engine.connect() as conn:
        last_login = (
            await conn.execute(
                text("SELECT last_login_at FROM identity.users WHERE id = :u"), {"u": user.id}
            )
        ).scalar_one()
    assert last_login == T0 + timedelta(days=2)


# --- Cierre de sesión ------------------------------------------------------------------------


async def test_logout_borra_la_cookie_y_revoca_la_sesion(app: FastAPI, login: Login) -> None:
    _, cookie = await login()
    async with client(app) as http:
        response = await http.post(
            "/api/auth/logout", headers={**XRW, "Cookie": f"{REFRESH_COOKIE}={cookie}"}
        )

    assert response.status_code == 204
    deleted = set_cookie(response)
    assert deleted["max-age"] == "0"
    assert deleted["path"] == "/api/auth"
    assert problem(await refresh(app, cookie)) == "session-revoked"


async def test_logout_sin_cookie_o_sin_cabecera_responde_401(app: FastAPI, login: Login) -> None:
    _, cookie = await login()
    async with client(app) as http:
        no_cookie = await http.post("/api/auth/logout", headers=XRW)
        no_header = await http.post(
            "/api/auth/logout", headers={"Cookie": f"{REFRESH_COOKIE}={cookie}"}
        )

    assert problem(no_cookie) == "unauthenticated"
    assert problem(no_header) == "unauthenticated"
    assert set_cookie(no_cookie)["max-age"] == "0"
    # Sin la cabecera no se revocó nada: la sesión sigue viva.
    assert (await refresh(app, cookie)).status_code == 200


# --- El token de acceso deja de servir al revocar la sesión (ASVS V3.3.1) ----------------------


async def access_token(app: FastAPI, cookie: str) -> tuple[str, str]:
    response = await refresh(app, cookie)
    assert response.status_code == 200
    return response.json()["access_token"], set_cookie(response).value


async def protected(app: FastAPI, token: str) -> httpx.Response:
    async with client(app) as http:
        return await http.get("/api/v1/protegido", headers={"Authorization": f"Bearer {token}"})


async def test_tras_logout_el_token_de_acceso_ya_no_sirve(app: FastAPI, login: Login) -> None:
    _, cookie = await login()
    token, cookie = await access_token(app, cookie)
    assert (await protected(app, token)).status_code == 200

    async with client(app) as http:
        await http.post("/api/auth/logout", headers={**XRW, "Cookie": f"{REFRESH_COOKIE}={cookie}"})

    assert problem(await protected(app, token)) == "session-revoked"


async def test_tras_reutilizar_un_token_el_de_acceso_ya_no_sirve(
    app: FastAPI, login: Login, clock: FixedClock
) -> None:
    _, first = await login()
    token, _ = await access_token(app, first)
    clock.advance(REUSE_GRACE + timedelta(seconds=1))

    assert problem(await refresh(app, first)) == "session-revoked"  # reutilización
    assert problem(await protected(app, token)) == "session-revoked"
