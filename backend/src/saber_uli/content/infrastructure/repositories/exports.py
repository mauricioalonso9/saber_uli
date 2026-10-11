"""Registros de solo inserción: exportaciones (data-model §2.10) y cambios de la taxonomía
(§2.11)."""

from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.application.ports import ExportRecord, TaxonomyChange
from saber_uli.content.infrastructure.orm import ExportRow, TaxonomyChangeRow


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


class SqlAlchemyTaxonomyChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, change: TaxonomyChange) -> None:
        self._db.add(
            TaxonomyChangeRow(
                changed_by=change.changed_by,
                changed_at=change.changed_at,
                target=change.target,
                target_id=change.target_id,
                action=change.action,
                before=change.before,
                after=change.after,
            )
        )
        await self._db.flush()
