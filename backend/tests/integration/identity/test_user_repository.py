"""T043: repositorio de usuarios con PostgreSQL real (data-model §2.1, §2.3; FR-005, FR-025)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, NullPool, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from saber_uli.identity.application.ports import UserAlreadyExistsError
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import InstitutionalIdentity, User, UserStatus
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.shared.infrastructure.db import Base

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
TENANT = UUID("11111111-1111-4111-8111-111111111111")


def identity(n: int) -> InstitutionalIdentity:
    return InstitutionalIdentity(tenant_id=TENANT, object_id=UUID(int=n))


def institutional(n: int, email: str | None = None) -> User:
    return User.new_institutional(
        identity(n), email=email or f"persona{n}@unilibre.edu.co", display_name=f"P{n}", now=NOW
    )


@pytest.fixture
def repo(db_session: AsyncSession) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db_session)


async def test_guardar_y_leer_con_roles(repo: SqlAlchemyUserRepository) -> None:
    user = institutional(1)
    user.grant_role(Role.TEACHER)

    saved = await repo.add(user)
    assert saved.id is not None
    loaded = await repo.get(saved.id)

    assert loaded is not None
    assert loaded is not user
    assert loaded.roles == {Role.STUDENT, Role.TEACHER}
    assert loaded.entra_identity == identity(1)
    assert (loaded.email, loaded.display_name, loaded.status) == (
        "persona1@unilibre.edu.co",
        "P1",
        UserStatus.ACTIVE,
    )
    assert loaded.created_at == NOW


async def test_save_persiste_cambios_de_estado_epoca_y_roles(
    repo: SqlAlchemyUserRepository,
) -> None:
    user = await repo.add(institutional(1))
    user.grant_role(Role.ADMIN)
    await repo.save(user)
    user.revoke_role(Role.ADMIN)
    user.disable()
    await repo.save(user)

    assert user.id is not None
    loaded = await repo.get(user.id)
    assert loaded is not None
    assert loaded.roles == {Role.STUDENT}
    assert loaded.status is UserStatus.DISABLED
    assert loaded.auth_epoch == 2


async def test_buscar_por_tid_y_oid(repo: SqlAlchemyUserRepository) -> None:
    await repo.add(institutional(1))

    found = await repo.get_by_entra_identity(identity(1))

    assert found is not None
    assert found.email == "persona1@unilibre.edu.co"
    assert await repo.get_by_entra_identity(identity(2)) is None


async def test_buscar_invitado_vigente_sin_distinguir_mayusculas(
    repo: SqlAlchemyUserRepository,
) -> None:
    guest = await repo.add(User.new_guest(email="Invitado@Correo.co", display_name=None, now=NOW))
    await repo.add(institutional(1, email="invitado@correo.co"))

    found = await repo.find_active_guest_by_email("  invitado@CORREO.co ")

    assert found is not None
    assert found.id == guest.id
    assert await repo.find_active_guest_by_email("nadie@correo.co") is None


async def test_la_lapida_se_guarda_sin_datos_personales_ni_roles(
    repo: SqlAlchemyUserRepository, db_session: AsyncSession
) -> None:
    user = await repo.add(institutional(1))
    user.request_deletion()
    user.to_tombstone()
    await repo.save(user)

    row = (
        await db_session.execute(
            text(
                """SELECT status, email, display_name, entra_object_id,
                          (SELECT count(*) FROM identity.role_assignments WHERE user_id = :id)
                   FROM identity.users WHERE id = :id"""
            ),
            {"id": user.id},
        )
    ).one()
    assert tuple(row) == ("deleted", None, None, None, 0)


async def test_get_de_un_id_inexistente(repo: SqlAlchemyUserRepository) -> None:
    assert await repo.get(UUID(int=999)) is None


# --- Bloqueo de administradores activos (FR-025) -----------------------------------------------


@pytest.fixture
async def committed_admins(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[list[UUID]]:
    """Dos administradores activos y uno desactivado, confirmados (el bloqueo se ve entre
    conexiones). saber_app no borra usuarios, así que la limpieza usa saber_migrator."""
    ids: list[UUID] = []
    async with AsyncSession(app_engine, expire_on_commit=False) as session:
        repo = SqlAlchemyUserRepository(session)
        for n, disabled in ((101, False), (102, False), (103, True)):
            user = institutional(n)
            user.grant_role(Role.ADMIN)
            if disabled:
                user.disable()
            await repo.add(user)
            assert user.id is not None
            ids.append(user.id)
        await session.commit()
    yield ids
    cleanup = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with cleanup.begin() as conn:
        await conn.execute(text("DELETE FROM identity.users WHERE id = ANY(:ids)"), {"ids": ids})
    await cleanup.dispose()


async def test_bloqueo_de_administradores_activos(
    app_engine: AsyncEngine, committed_admins: list[UUID]
) -> None:
    active = set(committed_admins[:2])
    async with AsyncSession(app_engine) as session:
        locked = await SqlAlchemyUserRepository(session).lock_active_admins()
        assert set(locked) >= active
        assert committed_admins[2] not in locked

        async with app_engine.connect() as other:
            with pytest.raises(DBAPIError, match="could not obtain lock"):
                await other.execute(
                    text("SELECT id FROM identity.users WHERE id = ANY(:ids) FOR UPDATE NOWAIT"),
                    {"ids": list(active)},
                )
        await session.rollback()


# --- El ORM coincide con las migraciones -------------------------------------------------------


def _diffs(connection: Connection) -> list[object]:
    def include_object(obj: object, name: str | None, type_: str, *_: object) -> bool:
        schema = getattr(obj, "schema", None) or getattr(
            getattr(obj, "table", None), "schema", None
        )
        return schema == "identity"

    context = MigrationContext.configure(
        connection,
        opts={
            "include_schemas": True,
            "include_object": include_object,
            "compare_type": True,
        },
    )
    return list(compare_metadata(context, Base.metadata))


async def test_el_orm_coincide_con_el_esquema_migrado(migrated_database: dict[str, str]) -> None:
    import saber_uli.identity.infrastructure.orm  # noqa: F401 - registra las tablas

    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.connect() as conn:
        diffs = await conn.run_sync(_diffs)
    await engine.dispose()

    assert diffs == []


async def test_la_identidad_institucional_duplicada_se_traduce(
    repo: SqlAlchemyUserRepository,
) -> None:
    await repo.add(institutional(1))

    with pytest.raises(UserAlreadyExistsError):
        await repo.add(institutional(1, email="otra@unilibre.edu.co"))
