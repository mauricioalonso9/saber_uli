"""T047: dependencia de autenticación (research R-15, R-16; FR-010, FR-029; escenario 5.4).

Usa PostgreSQL y Redis reales. Los datos se confirman (el autenticador abre sus propias
transacciones) y se limpian al final con `saber_migrator`.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from saber_uli.identity.application.access_guard import AccessGuard
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import AuthMethod, Session
from saber_uli.identity.domain.user import InstitutionalIdentity, User
from saber_uli.identity.infrastructure.epoch_cache import RedisEpochStore
from saber_uli.identity.infrastructure.repositories.sessions import SqlAlchemySessionRepository
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.identity.infrastructure.session_revocations import RedisSessionRevocations
from saber_uli.identity.infrastructure.tokens import AccessTokenClaims, AccessTokenCodec
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.api.auth import current_user, require_permission, require_privileged
from saber_uli.shared.api.problems import install_problem_handlers
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import TEST_JWT_KEY, TEST_JWT_KID

PROBLEM = "urn:saber-uli:problem:"
TENANT = UUID("11111111-1111-4111-8111-111111111111")
CODEC = AccessTokenCodec({TEST_JWT_KID: TEST_JWT_KEY}, active_kid=TEST_JWT_KID)


def build_app(guard: AccessGuard) -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)
    app.state.authenticator = guard

    @app.get("/api/v1/me")
    async def me(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "roles": sorted(user.roles),
            "permissions": sorted(user.permissions),
            "privileged": user.privileged,
        }

    @app.get("/api/v1/admin/users")
    async def admin(
        user: Annotated[AuthenticatedUser, Depends(require_privileged)],
    ) -> dict[str, str]:
        return {"id": str(user.id)}

    @app.get("/api/v1/admin/settings")
    async def settings(
        user: Annotated[AuthenticatedUser, Depends(require_permission("settings:manage"))],
    ) -> dict[str, str]:
        return {"id": str(user.id)}

    return app


@pytest.fixture
async def guard(app_engine: AsyncEngine, redis_url: str, redis_client: Redis) -> AccessGuard:
    factory = create_session_factory(app_engine)
    return AccessGuard(
        decoder=CODEC,
        epochs=RedisEpochStore(redis_url),
        revocations=RedisSessionRevocations(redis_url),
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus()),
        clock=SystemClock(),
    )


Committed = Callable[..., Awaitable[tuple[User, str]]]


@pytest.fixture
async def committed(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[Committed]:
    """Crea y confirma un usuario con una sesión; devuelve el usuario y su token de acceso."""
    created: list[UUID] = []

    async def create(
        *roles: Role, guest: bool = False, priv: bool = False, token_epoch: int | None = None
    ) -> tuple[User, str]:
        now = datetime.now(UTC)
        async with AsyncSession(app_engine, expire_on_commit=False) as db:
            if guest:
                user = User.new_guest(email=f"g-{uuid4()}@correo.co", display_name=None, now=now)
            else:
                user = User.new_institutional(
                    InstitutionalIdentity(tenant_id=TENANT, object_id=uuid4()),
                    email=f"p-{uuid4()}@unilibre.edu.co",
                    display_name="Persona",
                    now=now,
                )
                for role in roles:
                    user.grant_role(role)
            await SqlAlchemyUserRepository(db).add(user)
            assert user.id is not None
            session = await SqlAlchemySessionRepository(db).add(
                Session.start(user.id, AuthMethod.ENTRA_ID, now)
            )
            await db.commit()
        created.append(user.id)
        assert session.id is not None
        token = CODEC.encode(
            AccessTokenClaims(
                sub=user.id,
                sid=session.id,
                roles=tuple(sorted(r.value for r in user.roles)),
                epoch=user.auth_epoch if token_epoch is None else token_epoch,
                priv=priv,
                iat=now,
            )
        )
        return user, token

    yield create
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM identity.invitations"
                " WHERE guest_user_id = ANY(:ids) OR invited_by = ANY(:ids)"
            ),
            {"ids": created},
        )
        await conn.execute(
            text("DELETE FROM identity.users WHERE id = ANY(:ids)"), {"ids": created}
        )
    await engine.dispose()


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement), params)


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def problem_type(response: httpx.Response) -> str:
    assert response.status_code == 401, response.text
    return str(response.json()["type"]).removeprefix(PROBLEM)


# --- Token -------------------------------------------------------------------------------------


async def test_sin_token(guard: AccessGuard) -> None:
    async with client(build_app(guard)) as http:
        response = await http.get("/api/v1/me")

    assert problem_type(response) == "unauthenticated"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer no-es-jwt", "Basic dXN1YXJpbw==", "Bearer"])
async def test_token_invalido(guard: AccessGuard, header: str) -> None:
    async with client(build_app(guard)) as http:
        response = await http.get("/api/v1/me", headers={"Authorization": header})

    assert problem_type(response) == "unauthenticated"


async def test_token_valido(guard: AccessGuard, committed: Committed) -> None:
    user, token = await committed(Role.TEACHER)
    async with client(build_app(guard)) as http:
        response = await http.get("/api/v1/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "roles": ["student", "teacher"],
        "permissions": ["groups:read_own_students", "invitations:manage_own"],
        "privileged": False,
    }


# --- Época distinta: causa de la denegación (R-16) -------------------------------------------


async def test_cuenta_desactivada(
    guard: AccessGuard, committed: Committed, app_engine: AsyncEngine
) -> None:
    user, token = await committed()
    await sql(
        app_engine,
        "UPDATE identity.users SET status = 'disabled', auth_epoch = auth_epoch + 1 WHERE id = :u",
        u=user.id,
    )
    async with client(build_app(guard)) as http:
        assert (
            problem_type(await http.get("/api/v1/me", headers=bearer(token))) == "account-disabled"
        )


async def test_sesion_revocada_por_cambio_de_acceso(
    guard: AccessGuard, committed: Committed, app_engine: AsyncEngine
) -> None:
    user, token = await committed(Role.ADMIN)
    # Retirar un rol incrementa la época sin desactivar la cuenta.
    await sql(
        app_engine, "UPDATE identity.users SET auth_epoch = auth_epoch + 1 WHERE id = :u", u=user.id
    )
    async with client(build_app(guard)) as http:
        assert (
            problem_type(await http.get("/api/v1/me", headers=bearer(token))) == "session-revoked"
        )


async def test_cuenta_en_supresion(
    guard: AccessGuard, committed: Committed, app_engine: AsyncEngine
) -> None:
    user, token = await committed()
    await sql(
        app_engine,
        """UPDATE identity.users SET status = 'deletion_pending', auth_epoch = auth_epoch + 1
           WHERE id = :u""",
        u=user.id,
    )
    async with client(build_app(guard)) as http:
        assert (
            problem_type(await http.get("/api/v1/me", headers=bearer(token))) == "account-deleted"
        )


@pytest.mark.parametrize(
    ("status", "expires_in", "cause"),
    [
        ("revoked", timedelta(days=30), "guest-access-revoked"),
        ("expired", timedelta(days=30), "guest-access-expired"),
        ("accepted", -timedelta(minutes=1), "guest-access-expired"),
    ],
)
async def test_acceso_de_invitado(
    guard: AccessGuard,
    committed: Committed,
    app_engine: AsyncEngine,
    status: str,
    expires_in: timedelta,
    cause: str,
) -> None:
    inviter, _ = await committed(Role.TEACHER)
    guest, token = await committed(guest=True)
    await sql(
        app_engine,
        """INSERT INTO identity.invitations
               (email, invited_by, guest_user_id, status, access_expires_at, created_at)
           VALUES (NULL, :by, :g, :s, now() + :exp, now() - interval '60 days')""",
        by=inviter.id,
        g=guest.id,
        s=status,
        exp=expires_in,
    )
    await sql(
        app_engine,
        "UPDATE identity.users SET auth_epoch = auth_epoch + 1 WHERE id = :u",
        u=guest.id,
    )
    async with client(build_app(guard)) as http:
        assert problem_type(await http.get("/api/v1/me", headers=bearer(token))) == cause


# --- Sesión privilegiada (R-15) ----------------------------------------------------------------


async def test_ruta_privilegiada_sin_priv(guard: AccessGuard, committed: Committed) -> None:
    _, token = await committed(Role.ADMIN, priv=False)
    async with client(build_app(guard)) as http:
        response = await http.get("/api/v1/admin/users", headers=bearer(token))

    assert problem_type(response) == "reauthentication-required"


async def test_la_actividad_privilegiada_se_registra(
    guard: AccessGuard, committed: Committed, app_engine: AsyncEngine
) -> None:
    user, token = await committed(Role.ADMIN, priv=True)
    async with app_engine.connect() as conn:
        before = (
            await conn.execute(
                text(
                    "SELECT last_privileged_activity_at FROM identity.sessions WHERE user_id = :u"
                ),
                {"u": user.id},
            )
        ).scalar_one()

    async with client(build_app(guard)) as http:
        response = await http.get("/api/v1/admin/users", headers=bearer(token))

    assert response.status_code == 200
    async with app_engine.connect() as conn:
        after = (
            await conn.execute(
                text(
                    "SELECT last_privileged_activity_at FROM identity.sessions WHERE user_id = :u"
                ),
                {"u": user.id},
            )
        ).scalar_one()
    assert after > before


# --- Caché de la época en Redis con respaldo en la base -------------------------------------


async def test_la_epoca_se_guarda_en_redis(
    guard: AccessGuard, committed: Committed, redis_client: Redis
) -> None:
    user, token = await committed()
    async with client(build_app(guard)) as http:
        assert (await http.get("/api/v1/me", headers=bearer(token))).status_code == 200

    assert await redis_client.get(f"saber-uli:auth-epoch:{user.id}") == b"0"


async def test_si_redis_falla_se_usa_la_base_de_datos(
    app_engine: AsyncEngine, committed: Committed
) -> None:
    factory = create_session_factory(app_engine)
    guard = AccessGuard(
        decoder=CODEC,
        epochs=RedisEpochStore("redis://127.0.0.1:1/0"),
        revocations=RedisSessionRevocations("redis://127.0.0.1:1/0"),
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus()),
        clock=SystemClock(),
    )
    _, token = await committed()
    stale_user, stale_token = await committed(token_epoch=7)

    async with client(build_app(guard)) as http:
        ok = await http.get("/api/v1/me", headers=bearer(token))
        stale = await http.get("/api/v1/me", headers=bearer(stale_token))

    assert ok.status_code == 200
    assert problem_type(stale) == "session-revoked"
    assert stale_user.id is not None


# --- Permisos por ruta (ASVS V4.1.3; FR-030) ---------------------------------------------------


async def test_require_permission_niega_por_defecto(
    guard: AccessGuard, committed: Committed
) -> None:
    _, student = await committed()
    _, admin = await committed(Role.ADMIN)
    async with client(build_app(guard)) as http:
        denied = await http.get("/api/v1/admin/settings", headers=bearer(student))
        allowed = await http.get("/api/v1/admin/settings", headers=bearer(admin))

    assert denied.status_code == 403
    assert denied.json()["type"] == "urn:saber-uli:problem:forbidden"
    assert allowed.status_code == 200


async def test_una_sesion_revocada_invalida_su_token_de_acceso(
    guard: AccessGuard, committed: Committed, redis_url: str
) -> None:
    user, token = await committed()
    claims = CODEC.decode(token, now=datetime.now(UTC))
    await RedisSessionRevocations(redis_url).revoke(claims.sid)

    async with client(build_app(guard)) as http:
        response = await http.get("/api/v1/me", headers=bearer(token))

    assert problem_type(response) == "session-revoked"
    assert user.id == claims.sub
