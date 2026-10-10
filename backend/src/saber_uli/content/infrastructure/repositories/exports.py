"""Registro de las exportaciones del banco (data-model §2.10; solo inserción)."""

from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.application.ports import ExportRecord
from saber_uli.content.infrastructure.orm import ExportRow


class SqlAlchemyExportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, record: ExportRecord) -> None:
        self._db.add(
            ExportRow(
                created_by=record.created_by,
                created_at=record.created_at,
                format=record.format,
                filter=record.filter,
                version_choice=record.version_choice,
                item_count=record.item_count,
                skipped_count=record.skipped_count,
            )
        )
        await self._db.flush()
