"""Repositorio de auditoría: solo inserción (los permisos de `saber_app` lo garantizan, 0003)."""

from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.application.audit import AuditEntry
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
