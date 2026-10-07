"""Grupos, miembros y docentes (data-model §2.6)."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.application.ports import MemberContact, PersonName
from saber_uli.identity.domain.group import Group
from saber_uli.identity.infrastructure.orm import (
    GroupMemberRow,
    GroupRow,
    GroupTeacherRow,
    UserRow,
)
from saber_uli.shared.infrastructure.db import LIKE_ESCAPE, contains_pattern

LinkTable = type[GroupMemberRow] | type[GroupTeacherRow]


class SqlAlchemyGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, group: Group) -> Group:
        row = GroupRow(created_by=group.created_by, created_at=group.created_at)
        _copy(group, row)
        self._db.add(row)
        await self._db.flush()
        group.id = row.id
        return group

    async def save(self, group: Group) -> None:
        if group.id is None:
            raise ValueError("el grupo aún no se ha guardado; use add()")
        row = await self._db.get(GroupRow, group.id)
        if row is None:
            raise LookupError("el grupo no existe")
        _copy(group, row)
        await self._db.flush()

    async def get(self, group_id: UUID) -> Group | None:
        row = await self._db.get(GroupRow, group_id)
        return None if row is None else _to_domain(row)

    async def search(self, *, q: str | None, offset: int, limit: int) -> tuple[list[Group], int]:
        conditions = []
        if q:
            pattern = contains_pattern(q)
            conditions.append(
                func.lower(GroupRow.name).like(pattern, escape=LIKE_ESCAPE)
                | func.lower(GroupRow.cohort_label).like(pattern, escape=LIKE_ESCAPE)
            )
        total = await self._db.scalar(select(func.count()).select_from(GroupRow).where(*conditions))
        rows = await self._db.scalars(
            select(GroupRow)
            .where(*conditions)
            .order_by(GroupRow.created_at.desc(), GroupRow.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_domain(row) for row in rows], int(total or 0)

    async def member_count(self, group_id: UUID) -> int:
        count = await self._db.scalar(
            select(func.count())
            .select_from(GroupMemberRow)
            .where(GroupMemberRow.group_id == group_id)
        )
        return int(count or 0)

    async def teachers(self, group_id: UUID) -> list[PersonName]:
        rows = await self._db.execute(
            select(UserRow.id, UserRow.display_name)
            .join(GroupTeacherRow, GroupTeacherRow.user_id == UserRow.id)
            .where(GroupTeacherRow.group_id == group_id)
            .order_by(UserRow.display_name, UserRow.id)
        )
        return [PersonName(user_id=row.id, display_name=row.display_name) for row in rows]

    async def add_members(self, group_id: UUID, user_ids: Collection[UUID]) -> list[UUID]:
        return await self._link(GroupMemberRow, group_id, user_ids)

    async def remove_member(self, group_id: UUID, user_id: UUID) -> bool:
        return await self._unlink(GroupMemberRow, group_id, user_id)

    async def add_teachers(self, group_id: UUID, user_ids: Collection[UUID]) -> list[UUID]:
        return await self._link(GroupTeacherRow, group_id, user_ids)

    async def remove_teacher(self, group_id: UUID, user_id: UUID) -> bool:
        return await self._unlink(GroupTeacherRow, group_id, user_id)

    async def teaching_groups(self, user_id: UUID) -> list[Group]:
        rows = await self._db.scalars(
            select(GroupRow)
            .join(GroupTeacherRow, GroupTeacherRow.group_id == GroupRow.id)
            .where(GroupTeacherRow.user_id == user_id, GroupRow.archived_at.is_(None))
            .order_by(GroupRow.name, GroupRow.id)
        )
        return [_to_domain(row) for row in rows]

    async def is_teacher(self, group_id: UUID, user_id: UUID) -> bool:
        found = await self._db.scalar(
            select(GroupTeacherRow.user_id).where(
                GroupTeacherRow.group_id == group_id, GroupTeacherRow.user_id == user_id
            )
        )
        return found is not None

    async def students(
        self, group_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[PersonName], int]:
        total = await self.member_count(group_id)
        rows = await self._db.execute(
            select(UserRow.id, UserRow.display_name)
            .join(GroupMemberRow, GroupMemberRow.user_id == UserRow.id)
            .where(GroupMemberRow.group_id == group_id)
            .order_by(UserRow.display_name, UserRow.id)
            .offset(offset)
            .limit(limit)
        )
        people = [PersonName(user_id=row.id, display_name=row.display_name) for row in rows]
        return people, total

    async def members(
        self, group_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[MemberContact], int]:
        total = await self.member_count(group_id)
        rows = await self._db.execute(
            select(UserRow.id, UserRow.display_name, UserRow.email)
            .join(GroupMemberRow, GroupMemberRow.user_id == UserRow.id)
            .where(GroupMemberRow.group_id == group_id)
            .order_by(UserRow.display_name, UserRow.id)
            .offset(offset)
            .limit(limit)
        )
        people = [
            MemberContact(user_id=row.id, display_name=row.display_name, email=row.email)
            for row in rows
        ]
        return people, total

    async def _link(self, table: LinkTable, group_id: UUID, ids: Collection[UUID]) -> list[UUID]:
        if not ids:
            return []
        result = await self._db.execute(
            insert(table)
            .values([{"group_id": group_id, "user_id": user_id} for user_id in ids])
            .on_conflict_do_nothing()
            .returning(table.user_id)
        )
        return list(result.scalars())

    async def _unlink(self, table: LinkTable, group_id: UUID, user_id: UUID) -> bool:
        result = await self._db.execute(
            delete(table).where(table.group_id == group_id, table.user_id == user_id)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]


def _copy(group: Group, row: GroupRow) -> None:
    row.name = group.name
    row.description = group.description
    row.cohort_label = group.cohort_label
    row.program_id = group.program_id
    row.archived_at = group.archived_at


def _to_domain(row: GroupRow) -> Group:
    return Group(
        id=row.id,
        name=row.name,
        created_by=row.created_by,
        created_at=row.created_at,
        description=row.description,
        cohort_label=row.cohort_label,
        program_id=row.program_id,
        archived_at=row.archived_at,
    )
