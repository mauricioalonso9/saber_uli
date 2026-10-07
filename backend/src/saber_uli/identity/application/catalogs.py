"""Catálogos de administración: programas (FR-028), parámetros (FR-006a, R-29) y consulta de
auditoría (FR-035, solo lectura). Todo cambio queda auditado (SC-004).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import AuditRecord
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import NotFoundError


class ProgramNotFoundError(NotFoundError):
    slug = "not-found"


class ProgramAdmin:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def list(self, *, q: str | None, offset: int, limit: int) -> tuple[list[Program], int]:
        async with self._uow_factory() as uow:
            return await uow.programs.search(q=q, offset=offset, limit=limit)

    async def create(
        self, actor_id: UUID, *, code: str, name: str, campus: str, active: bool = True
    ) -> Program:
        async with self._uow_factory() as uow:
            program = await uow.programs.add(
                Program.new(code=code, name=name, campus=campus, active=active)
            )
            await self._audit(uow, AuditAction.PROGRAM_CREATED, program, actor_id)
            await uow.commit()
        return program

    async def update(
        self,
        actor_id: UUID,
        program_id: UUID,
        *,
        name: str | None = None,
        campus: str | None = None,
        active: bool | None = None,
    ) -> Program:
        async with self._uow_factory() as uow:
            program = await uow.programs.get(program_id)
            if program is None:
                raise ProgramNotFoundError("El programa no existe.")
            changed = program.describe(
                name=program.name if name is None else name,
                campus=program.campus if campus is None else campus,
            )
            if active is not None and active != program.active:
                program.active = active
                changed = True
            if changed:
                await uow.programs.save(program)
                await self._audit(uow, AuditAction.PROGRAM_UPDATED, program, actor_id)
                await uow.commit()
        return program

    async def _audit(
        self, uow: IdentityUnitOfWork, action: AuditAction, program: Program, actor_id: UUID
    ) -> None:
        await record_audit(
            uow,
            action,
            target=AuditTarget.PROGRAM,
            target_id=program.id,
            actor_id=actor_id,
            details={"code": program.code, "active": program.active},
            now=self._clock.now(),
        )


class SettingsAdmin:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def get(self) -> IdentitySettings:
        async with self._uow_factory() as uow:
            return await uow.settings.load()

    async def update(self, actor_id: UUID, changes: dict[str, int]) -> IdentitySettings:
        """Valida los rangos (`SettingOutOfRangeError`) y audita cada parámetro que cambió."""
        now = self._clock.now()
        async with self._uow_factory() as uow:
            previous = await uow.settings.load()
            updated = previous.with_changes(**changes)
            changed = sorted(updated.changed_keys(previous))
            if changed:
                await uow.settings.save(updated, previous=previous, updated_by=actor_id)
                before, after = previous.as_dict(), updated.as_dict()
                for key in changed:
                    await record_audit(
                        uow,
                        AuditAction.SETTING_CHANGED,
                        target=AuditTarget.SETTING,
                        actor_id=actor_id,
                        details={"key": key, "before": before[key], "after": after[key]},
                        now=now,
                    )
                await uow.commit()
        return updated


@dataclass(frozen=True)
class AuditFilters:
    action: str | None = None
    actor_id: UUID | None = None
    subject_user_id: UUID | None = None
    since: datetime | None = None
    until: datetime | None = None


class AuditQuery:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def list(
        self, filters: AuditFilters, *, offset: int, limit: int
    ) -> tuple[list[AuditRecord], int]:
        async with self._uow_factory() as uow:
            options: dict[str, Any] = {
                "action": filters.action,
                "actor_id": filters.actor_id,
                "subject_user_id": filters.subject_user_id,
                "since": filters.since,
                "until": filters.until,
            }
            return await uow.audit.search(**options, offset=offset, limit=limit)
