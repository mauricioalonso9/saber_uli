"""Fixtures de integración (T024): PostgreSQL 18 y Redis 8 reales con Testcontainers.

- `postgres_container` aplica los scripts de `infra/postgres/init/` (roles y extensiones) con
  contraseñas generadas al vuelo, como en Compose.
- Motores por rol: `app_engine` (`saber_app`, DML) y `migrator_engine` (`saber_migrator`, DDL),
  por prueba y con `NullPool` (un motor de sesión quedaría atado a otro bucle de eventos).
- `db_session`: sesión de `saber_app` dentro de una transacción que se revierte al terminar.
- `migrated_database`: aplica las migraciones con `saber_migrator` (disponible desde T026).

Sin Docker, todo `tests/integration/` se omite, salvo con `REQUIRE_DOCKER=1`.
- `user_factory`: crea usuarios por rol en la sesión de la prueba (T044).

- `token_codec` y `issue_token`: tokens de acceso de prueba con una sesión real (T046).

Fixture que agrega otra tarea: cliente ASGI (T058).
"""

import asyncio
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import NullPool, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import AuthMethod, Session
from saber_uli.identity.domain.user import InstitutionalIdentity, User
from saber_uli.identity.infrastructure.repositories.sessions import SqlAlchemySessionRepository
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.identity.infrastructure.tokens import AccessTokenClaims, AccessTokenCodec
from tests._docker import docker_available, docker_required, require_docker, skip_without_docker

REPO = Path(__file__).resolve().parents[3]
INIT_SCRIPTS = REPO / "infra" / "postgres" / "init"
DB_NAME = "saber_uli"
ROLES = ("migrator", "app", "bi")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    here = Path(__file__).parent
    skip = skip_without_docker()
    for item in items:
        if here in Path(str(item.path)).parents:
            item.add_marker(pytest.mark.integration)
            item.add_marker(skip)


@pytest.fixture(scope="session")
def role_passwords() -> dict[str, str]:
    return {role: secrets.token_urlsafe(24) for role in ("superuser", *ROLES)}


async def _wait_for_role(url: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with asyncio.timeout(60):
            while True:
                try:
                    async with engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                    return
                except (OSError, SQLAlchemyError):
                    await asyncio.sleep(0.5)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def postgres_container(role_passwords: dict[str, str]) -> Iterator[PostgresContainer]:
    if docker_required() and not docker_available():
        require_docker()
    container = (
        PostgresContainer(
            "postgres:18",
            username="postgres",
            password=role_passwords["superuser"],
            dbname=DB_NAME,
            driver=None,
        )
        .with_env("SABER_MIGRATOR_PASSWORD", role_passwords["migrator"])
        .with_env("SABER_APP_PASSWORD", role_passwords["app"])
        .with_env("SABER_BI_PASSWORD", role_passwords["bi"])
        .with_volume_mapping(str(INIT_SCRIPTS), "/docker-entrypoint-initdb.d", "ro")
        .with_command("postgres -c shared_preload_libraries=pg_stat_statements")
    )
    with container:
        yield container


@pytest.fixture(scope="session")
def database_urls(
    postgres_container: PostgresContainer, role_passwords: dict[str, str]
) -> dict[str, str]:
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    urls = {
        role: (f"postgresql+asyncpg://saber_{role}:{role_passwords[role]}@{host}:{port}/{DB_NAME}")
        for role in ROLES
    }
    # Los roles los crea el script de inicio; se espera a poder entrar como saber_app.
    asyncio.run(_wait_for_role(urls["app"]))
    return urls


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    if docker_required() and not docker_available():
        require_docker()
    with RedisContainer("redis:8-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def migrated_database(database_urls: dict[str, str]) -> dict[str, str]:
    """Aplica `alembic upgrade head` con saber_migrator (T026). Úsese desde T025 en adelante."""
    from saber_uli.shared.infrastructure.migrations import run_migrations

    run_migrations(database_urls["migrator"])
    return database_urls


@pytest.fixture
async def app_engine(migrated_database: dict[str, str]) -> AsyncIterator[AsyncEngine]:
    """Motor de saber_app sobre la base ya migrada (tablas y permisos de 0003)."""
    engine = create_async_engine(migrated_database["app"], poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def migrator_engine(database_urls: dict[str, str]) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_urls["migrator"], poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(app_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sesión de saber_app; todo lo que haga la prueba se revierte al terminar."""
    async with app_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


TEST_TENANT = UUID("11111111-1111-4111-8111-111111111111")
UserFactory = Callable[..., Awaitable[User]]


@pytest.fixture
def user_factory(db_session: AsyncSession) -> UserFactory:
    """Crea y guarda un usuario con los roles indicados (por defecto, estudiante institucional).

    `await user_factory(Role.TEACHER, Role.ADMIN)`; `await user_factory(Role.GUEST)` crea un
    invitado. Los correos y `oid` son únicos y ficticios.
    """
    repo = SqlAlchemyUserRepository(db_session)
    now = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)

    async def create(*roles: Role, status_disabled: bool = False) -> User:
        unique = uuid4()
        if Role.GUEST in roles:
            user = User.new_guest(email=f"invitado-{unique}@correo.co", display_name=None, now=now)
        else:
            user = User.new_institutional(
                InstitutionalIdentity(tenant_id=TEST_TENANT, object_id=unique),
                email=f"persona-{unique}@unilibre.edu.co",
                display_name=f"Persona {str(unique)[:8]}",
                now=now,
            )
            for role in roles:
                user.grant_role(role)
        if status_disabled:
            user.disable()
        return await repo.add(user)

    return create


TEST_JWT_KID = "test"
TEST_JWT_KEY = b"clave-de-firma-de-prueba-de-256-bits-o-mas!!"
TokenIssuer = Callable[..., Awaitable[str]]


@pytest.fixture
def token_codec() -> AccessTokenCodec:
    return AccessTokenCodec({TEST_JWT_KID: TEST_JWT_KEY}, active_kid=TEST_JWT_KID)


@pytest.fixture
def issue_token(db_session: AsyncSession, token_codec: AccessTokenCodec) -> TokenIssuer:
    """Abre una sesión real para el usuario y devuelve un token de acceso firmado.

    `await issue_token(user, priv=True, epoch=0, issued_at=...)`. Por defecto usa la época
    vigente del usuario, `priv=False` y la hora actual.
    """
    sessions = SqlAlchemySessionRepository(db_session)

    async def issue(
        user: User,
        *,
        priv: bool = False,
        epoch: int | None = None,
        issued_at: datetime | None = None,
    ) -> str:
        assert user.id is not None
        when = issued_at or datetime.now(UTC)
        session = await sessions.add(Session.start(user.id, AuthMethod.ENTRA_ID, when))
        assert session.id is not None
        claims = AccessTokenClaims(
            sub=user.id,
            sid=session.id,
            roles=tuple(sorted(role.value for role in user.roles)),
            epoch=user.auth_epoch if epoch is None else epoch,
            priv=priv,
            iat=when,
        )
        return token_codec.encode(claims)

    return issue
