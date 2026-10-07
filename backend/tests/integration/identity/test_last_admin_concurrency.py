"""T136: dos administradores se quitan el rol mutuamente a la vez (FR-025).

Con solo dos administradores activos, exactamente una de las dos transacciones debe fallar con
`last-admin`: nunca puede quedar el sistema sin administradores. Las dos corren a la vez en
conexiones distintas; la regla se apoya en `lock_active_admins` (`FOR UPDATE`).
"""

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.application.admin_users import AdminUsersService, LastAdminError
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import CommittedLogin


@pytest.fixture
def service(app_engine: AsyncEngine) -> AdminUsersService:
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    uow_factory: Callable[[], Any] = lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus)  # noqa: E731
    return AdminUsersService(uow_factory=uow_factory, clock=SystemClock())


async def active_admins(engine: AsyncEngine) -> set[UUID]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT u.id FROM identity.users u
                   JOIN identity.role_assignments r ON r.user_id = u.id
                   WHERE r.role = 'admin' AND u.status = 'active'"""
            )
        )
        return {UUID(str(row.id)) for row in rows}


@pytest.mark.parametrize("round_", range(5))
async def test_exactamente_una_de_dos_revocaciones_cruzadas_falla(
    service: AdminUsersService,
    committed_login: CommittedLogin,
    app_engine: AsyncEngine,
    round_: int,
) -> None:
    assert await active_admins(app_engine) == set(), "otra prueba dejó administradores"
    a, _ = await committed_login(Role.ADMIN)
    b, _ = await committed_login(Role.ADMIN)
    assert a.id is not None and b.id is not None

    results = await asyncio.gather(
        service.set_roles(a.id, b.id, {Role.STUDENT}, director_program_ids=set()),
        service.set_roles(b.id, a.id, {Role.STUDENT}, director_program_ids=set()),
        return_exceptions=True,
    )

    failures = [r for r in results if isinstance(r, BaseException)]
    assert len(failures) == 1, results
    assert isinstance(failures[0], LastAdminError)
    assert len(await active_admins(app_engine)) == 1


async def test_desactivar_y_revocar_cruzados_tambien_dejan_un_administrador(
    service: AdminUsersService, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    a, _ = await committed_login(Role.ADMIN)
    b, _ = await committed_login(Role.ADMIN)
    assert a.id is not None and b.id is not None

    results = await asyncio.gather(
        service.set_status(a.id, b.id, "disabled"),
        service.set_roles(b.id, a.id, {Role.STUDENT}, director_program_ids=set()),
        return_exceptions=True,
    )

    assert sum(isinstance(r, LastAdminError) for r in results) == 1, results
    assert len(await active_admins(app_engine)) == 1
