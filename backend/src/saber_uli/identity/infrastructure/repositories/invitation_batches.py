"""Lotes de invitaciones (data-model §2.9). Las filas se guardan en `rows` (jsonb); contienen
correos, por eso los lotes se purgan 30 días después de confirmados o vencidos."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.invitation_batch import (
    BatchRow,
    BatchStatus,
    InvitationBatch,
    RowResult,
)
from saber_uli.identity.infrastructure.orm import InvitationBatchRow


class SqlAlchemyInvitationBatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, batch: InvitationBatch) -> InvitationBatch:
        row = InvitationBatchRow(created_by=batch.created_by, created_at=batch.created_at)
        _copy(batch, row)
        self._db.add(row)
        await self._db.flush()
        batch.id = row.id
        return batch

    async def save(self, batch: InvitationBatch) -> None:
        if batch.id is None:
            raise ValueError("el lote aún no se ha guardado; use add()")
        row = await self._db.get(InvitationBatchRow, batch.id)
        if row is None:
            raise LookupError("el lote no existe")
        _copy(batch, row)
        await self._db.flush()

    async def get(self, batch_id: UUID) -> InvitationBatch | None:
        row = await self._db.get(InvitationBatchRow, batch_id)
        return None if row is None else _to_domain(row)

    async def get_for_update(self, batch_id: UUID) -> InvitationBatch | None:
        row = await self._db.scalar(
            select(InvitationBatchRow).where(InvitationBatchRow.id == batch_id).with_for_update()
        )
        return None if row is None else _to_domain(row)


def _row_to_json(row: BatchRow) -> dict[str, Any]:
    return {
        "line": row.line,
        "email": row.email,
        "name": row.name,
        "access_expires_at": (row.access_expires_at.isoformat() if row.access_expires_at else None),
        "result": row.result.value,
        "message": row.message,
    }


def _row_from_json(data: dict[str, Any]) -> BatchRow:
    expires = data.get("access_expires_at")
    return BatchRow(
        line=int(data["line"]),
        email=str(data["email"]),
        result=RowResult(data["result"]),
        name=data.get("name"),
        access_expires_at=datetime.fromisoformat(expires) if expires else None,
        message=data.get("message"),
    )


def _copy(batch: InvitationBatch, row: InvitationBatchRow) -> None:
    row.status = batch.status.value
    row.rows = [_row_to_json(item) for item in batch.rows]
    row.valid_count = batch.valid_count
    row.invalid_count = batch.invalid_count
    row.expires_at = batch.expires_at
    row.confirmed_at = batch.confirmed_at


def _to_domain(row: InvitationBatchRow) -> InvitationBatch:
    return InvitationBatch(
        id=row.id,
        created_by=row.created_by,
        status=BatchStatus(row.status),
        rows=[_row_from_json(item) for item in row.rows],
        expires_at=row.expires_at,
        created_at=row.created_at,
        confirmed_at=row.confirmed_at,
    )
