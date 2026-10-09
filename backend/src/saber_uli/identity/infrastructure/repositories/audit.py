"""Repositorio de auditoría: solo inserción (los permisos de `saber_app` lo garantizan, 0003)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.application.audit import AuditEntry
from saber_uli.identity.application.ports import AuditRecord
from saber_uli.identity.infrastructure.orm import AuditEventRow


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, entry: AuditEntry) -> None:
        self._db.add(
            AuditEventRow(
                occurred_at=entry.occurred_at,
                actor_id=entry.actor_id,
                action=entry.action.value,
                target_type=entry.target.value,
                target_id=entry.target_id,
                subject_user_id=entry.subject_user_id,
                details=dict(entry.details),
            )
        )
        await self._db.flush()

    async def search(
        self,
        *,
        action: str | None,
        actor_id: UUID | None,
        subject_user_id: UUID | None,
        since: datetime | None,
        until: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AuditRecord], int]:
        conditions = []
        if action:
            conditions.append(AuditEventRow.action == action)
        if actor_id is not None:
            conditions.append(AuditEventRow.actor_id == actor_id)
        if subject_user_id is not None:
            conditions.append(AuditEventRow.subject_user_id == subject_user_id)
        if since is not None:
            conditions.append(AuditEventRow.occurred_at >= since)
        if until is not None:
            conditions.append(AuditEventRow.occurred_at <= until)
        total = await self._db.scalar(
            select(func.count()).select_from(AuditEventRow).where(*conditions)
        )
        rows = await self._db.scalars(
            select(AuditEventRow)
            .where(*conditions)
            .order_by(AuditEventRow.occurred_at.desc(), AuditEventRow.id.desc())
            .offset(offset)
            .limit(limit)
        )
        records = [
            AuditRecord(
                id=row.id,
                occurred_at=row.occurred_at,
                actor_id=row.actor_id,
                action=row.action,
                target_type=row.target_type,
                target_id=row.target_id,
                subject_user_id=row.subject_user_id,
                details=dict(row.details or {}),
            )
            for row in rows
        ]
        return records, int(total or 0)
