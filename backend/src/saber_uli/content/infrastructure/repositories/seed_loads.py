"""Registro de las cargas del banco inicial (data-model §2.12; solo inserción)."""

from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.application.ports import SeedLoadRecord
from saber_uli.content.infrastructure.orm import SeedLoadRow


class SqlAlchemySeedLoadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, record: SeedLoadRecord) -> None:
        self._db.add(
            SeedLoadRow(
                loaded_at=record.loaded_at,
                file_sha256=record.file_sha256,
                schema_version=record.schema_version,
                summary=record.summary,
                pending_manual=record.pending_manual,
            )
        )
        await self._db.flush()
