"""Repositorio de parámetros (data-model §2.15). Una clave ausente toma su valor por defecto."""

from dataclasses import fields
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.infrastructure.orm import SettingRow

_KEYS = tuple(f.name for f in fields(IdentitySettings))


class SqlAlchemySettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def load(self) -> IdentitySettings:
        rows = await self._db.execute(
            select(SettingRow.key, SettingRow.value).where(SettingRow.key.in_(_KEYS))
        )
        stored = {row.key: row.value for row in rows}
        return IdentitySettings(**stored)

    async def save(
        self, settings: IdentitySettings, *, previous: IdentitySettings, updated_by: UUID | None
    ) -> None:
        values = settings.as_dict()
        for key in sorted(settings.changed_keys(previous)):
            statement = insert(SettingRow).values(key=key, value=values[key], updated_by=updated_by)
            await self._db.execute(
                statement.on_conflict_do_update(
                    index_elements=[SettingRow.key],
                    set_={"value": values[key], "updated_by": updated_by, "updated_at": func.now()},
                )
            )
