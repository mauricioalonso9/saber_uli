"""Grupos o cohortes (FR-027; SC-004).

- El administrador crea, edita y archiva grupos, agrega y quita estudiantes institucionales y
  asocia docentes. Todo queda auditado (`group.*`).
- Un docente ve solo sus grupos y, de sus estudiantes, el nombre: nunca el correo. Un grupo
  ajeno responde "no encontrado".
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import MemberContact, PersonName
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.group import (
    Group,
    NotATeacherError,
    NotInstitutionalStudentError,
    ensure_member,
    ensure_teacher,
)
from saber_uli.identity.domain.user import User
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import NotFoundError


class GroupNotFoundError(NotFoundError):
    slug = "not-found"


@dataclass(frozen=True)
class GroupView:
    group: Group
    member_count: int
    teachers: list[PersonName]


class GroupService:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def members(
        self, group_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[MemberContact], int]:
        async with self._uow_factory() as uow:
            await _existing(uow, group_id)
            return await uow.groups.members(group_id, offset=offset, limit=limit)

    async def list(self, *, q: str | None, offset: int, limit: int) -> tuple[list[GroupView], int]:
        async with self._uow_factory() as uow:
            groups, total = await uow.groups.search(q=q, offset=offset, limit=limit)
            return [await _view(uow, group) for group in groups], total

    async def get(self, group_id: UUID) -> GroupView:
        async with self._uow_factory() as uow:
            return await _view(uow, await _existing(uow, group_id))

    async def create(
        self,
        actor_id: UUID,
        *,
        name: str,
        description: str | None = None,
        cohort_label: str | None = None,
        program_id: UUID | None = None,
    ) -> GroupView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            group = await uow.groups.add(
                Group.create(
                    name=name,
                    created_by=actor_id,
                    now=now,
                    description=description,
                    cohort_label=cohort_label,
                    program_id=program_id,
                )
            )
            await self._audit(uow, AuditAction.GROUP_CREATED, group, actor_id)
            view = await _view(uow, group)
            await uow.commit()
        return view

    async def update(self, actor_id: UUID, group_id: UUID, **changes: object) -> GroupView:
        """`changes`: `name`, `description`, `cohort_label` y `archived`, solo los indicados."""
        now = self._clock.now()
        async with self._uow_factory() as uow:
            group = await _existing(uow, group_id)
            was_archived = group.archived_at is not None
            group.update(now=now, **changes)  # type: ignore[arg-type]
            await uow.groups.save(group)
            archived_now = group.archived_at is not None and not was_archived
            await self._audit(
                uow,
                AuditAction.GROUP_ARCHIVED if archived_now else AuditAction.GROUP_UPDATED,
                group,
                actor_id,
            )
            view = await _view(uow, group)
            await uow.commit()
        return view

    async def add_members(
        self, actor_id: UUID, group_id: UUID, user_ids: Sequence[UUID]
    ) -> GroupView:
        return await self._add(actor_id, group_id, user_ids, teachers=False)

    async def add_teachers(
        self, actor_id: UUID, group_id: UUID, user_ids: Sequence[UUID]
    ) -> GroupView:
        return await self._add(actor_id, group_id, user_ids, teachers=True)

    async def remove_member(self, actor_id: UUID, group_id: UUID, user_id: UUID) -> None:
        await self._remove(actor_id, group_id, user_id, teachers=False)

    async def remove_teacher(self, actor_id: UUID, group_id: UUID, user_id: UUID) -> None:
        await self._remove(actor_id, group_id, user_id, teachers=True)

    # --- Auxiliares -----------------------------------------------------------------------

    async def _add(
        self, actor_id: UUID, group_id: UUID, user_ids: Sequence[UUID], *, teachers: bool
    ) -> GroupView:
        async with self._uow_factory() as uow:
            group = await _existing(uow, group_id)
            for user_id in user_ids:
                user = await uow.users.get(user_id)
                _check(user, teachers=teachers)
            add = uow.groups.add_teachers if teachers else uow.groups.add_members
            added = await add(group_id, user_ids)
            action = AuditAction.GROUP_TEACHER_ADDED if teachers else AuditAction.GROUP_MEMBER_ADDED
            for user_id in added:
                await self._audit(uow, action, group, actor_id, subject=user_id)
            view = await _view(uow, group)
            await uow.commit()
        return view

    async def _remove(
        self, actor_id: UUID, group_id: UUID, user_id: UUID, *, teachers: bool
    ) -> None:
        async with self._uow_factory() as uow:
            group = await _existing(uow, group_id)
            remove = uow.groups.remove_teacher if teachers else uow.groups.remove_member
            if not await remove(group_id, user_id):
                raise GroupNotFoundError("Esa persona no está en el grupo.")
            action = (
                AuditAction.GROUP_TEACHER_REMOVED if teachers else AuditAction.GROUP_MEMBER_REMOVED
            )
            await self._audit(uow, action, group, actor_id, subject=user_id)
            await uow.commit()

    async def _audit(
        self,
        uow: IdentityUnitOfWork,
        action: AuditAction,
        group: Group,
        actor_id: UUID,
        *,
        subject: UUID | None = None,
    ) -> None:
        await record_audit(
            uow,
            action,
            target=AuditTarget.GROUP,
            target_id=group.id,
            subject_user_id=subject,
            actor_id=actor_id,
            now=self._clock.now(),
        )


class TeacherGroups:
    """Lo que ve un docente de sus grupos (FR-027)."""

    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def groups(self, teacher_id: UUID) -> list[tuple[Group, int]]:
        async with self._uow_factory() as uow:
            groups = await uow.groups.teaching_groups(teacher_id)
            return [(g, await uow.groups.member_count(g.id)) for g in groups if g.id is not None]

    async def students(
        self, teacher_id: UUID, group_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[PersonName], int]:
        async with self._uow_factory() as uow:
            if not await uow.groups.is_teacher(group_id, teacher_id):
                raise GroupNotFoundError("El grupo no existe.")
            return await uow.groups.students(group_id, offset=offset, limit=limit)


def _check(user: User | None, *, teachers: bool) -> None:
    if user is None:
        raise (NotATeacherError if teachers else NotInstitutionalStudentError)(
            "Una de las personas elegidas no existe."
        )
    (ensure_teacher if teachers else ensure_member)(user)


async def _existing(uow: IdentityUnitOfWork, group_id: UUID) -> Group:
    group = await uow.groups.get(group_id)
    if group is None:
        raise GroupNotFoundError("El grupo no existe.")
    return group


async def _view(uow: IdentityUnitOfWork, group: Group) -> GroupView:
    if group.id is None:
        raise ValueError("el grupo no está guardado")
    return GroupView(
        group=group,
        member_count=await uow.groups.member_count(group.id),
        teachers=await uow.groups.teachers(group.id),
    )
