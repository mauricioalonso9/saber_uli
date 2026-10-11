"""002/T007: nombres para mostrar desde la fachada de `identity` (research 002/R-14).

`content` guarda solo identificadores de personas y pide los nombres aquí: una cuenta suprimida
(lápida) aparece como "Cuenta eliminada" y los identificadores desconocidos se omiten. Una sola
consulta sirve para cualquier número de identificadores.
"""

from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from saber_uli.identity.application.directory import (
    DELETED_ACCOUNT_NAME,
    UNNAMED_ACCOUNT_NAME,
    IdentityDirectory,
)
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import CommittedLogin


async def test_devuelve_los_nombres_marca_las_cuentas_suprimidas_y_omite_las_desconocidas(
    committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    teacher, _ = await committed_login(Role.TEACHER)
    admin, _ = await committed_login(Role.ADMIN)
    assert teacher.id is not None and admin.id is not None
    erased, _ = await committed_login(Role.STUDENT)
    assert erased.id is not None
    async with AsyncSession(app_engine, expire_on_commit=False) as db:
        repo = SqlAlchemyUserRepository(db)
        stored = await repo.get(erased.id)
        assert stored is not None
        stored.request_deletion()
        stored.to_tombstone()
        await repo.save(stored)
        await db.commit()
    assert erased.id is not None
    unknown = uuid4()

    statements: list[str] = []

    def count(*args: object) -> None:
        statements.append(str(args[2]))

    event.listen(app_engine.sync_engine, "before_cursor_execute", count)
    factory = create_session_factory(app_engine)
    directory = IdentityDirectory(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus())
    )
    try:
        names = await directory.display_names({teacher.id, admin.id, erased.id, unknown})
    finally:
        event.remove(app_engine.sync_engine, "before_cursor_execute", count)

    assert names == {
        teacher.id: teacher.display_name,
        admin.id: admin.display_name,
        erased.id: DELETED_ACCOUNT_NAME,
    }
    assert DELETED_ACCOUNT_NAME == "Cuenta eliminada"
    assert sum("identity.users" in sql for sql in statements) == 1


async def test_sin_identificadores_no_consulta(app_engine: AsyncEngine) -> None:
    factory = create_session_factory(app_engine)
    directory = IdentityDirectory(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus())
    )

    assert await directory.display_names(set()) == {}


async def test_una_cuenta_sin_nombre_tiene_un_texto_neutro(
    committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    guest, _ = await committed_login(guest=True)
    assert guest.id is not None
    factory = create_session_factory(app_engine)
    directory = IdentityDirectory(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus())
    )

    assert await directory.display_names({guest.id}) == {guest.id: UNNAMED_ACCOUNT_NAME}
