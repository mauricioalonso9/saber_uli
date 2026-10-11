"""Lo que `content` guarda de una persona, para «Mis datos» (FR-031 de 001; research R-14).

Solo filas donde la persona aparece por su UUID: versiones en que participó, sus eventos (con el
comentario o motivo que ella escribió), sus importaciones, exportaciones y cambios de taxonomía.
Nunca el texto de los ítems ni lo que escribieron otras personas. Los nombres de archivo de las
importaciones quedan fuera (pueden nombrar a terceros, principio V).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Uuid, any_, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.infrastructure.orm import (
    ExportRow,
    ImportRow,
    ItemEventRow,
    ItemRow,
    ItemVersionRow,
    TaxonomyChangeRow,
)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


class SqlAlchemyPersonalDataReader:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def collect(self, user_id: UUID) -> dict[str, Any]:
        return {
            "versiones": await self._versions(user_id),
            "eventos": await self._events(user_id),
            "importaciones": await self._imports(user_id),
            "exportaciones": await self._exports(user_id),
            "cambios_taxonomia": await self._taxonomy_changes(user_id),
        }

    async def _versions(self, user_id: UUID) -> list[dict[str, Any]]:
        v = ItemVersionRow
        rows = await self._db.execute(
            select(ItemRow.code, v.number, v.state, v.author_id, v.contributor_ids)
            .add_columns(v.reviewed_by, v.retired_by)
            .join(ItemRow, ItemRow.id == v.item_id)
            .where(
                or_(
                    v.author_id == user_id,
                    literal(user_id, Uuid) == any_(v.contributor_ids),
                    v.reviewed_by == user_id,
                    v.retired_by == user_id,
                )
            )
            .order_by(ItemRow.code, v.number)
        )
        versions = []
        for code, number, state, author, contributors, reviewer, retirer in rows:
            roles = []
            if author == user_id:
                roles.append("autor")
            elif user_id in (contributors or []):
                roles.append("colaborador")
            if reviewer == user_id:
                roles.append("revisor")
            if retirer == user_id:
                roles.append("retiro")
            versions.append(
                {"item": code, "version": number, "estado": state, "participacion": roles}
            )
        return versions

    async def _events(self, user_id: UUID) -> list[dict[str, Any]]:
        e = ItemEventRow
        rows = await self._db.execute(
            select(ItemRow.code, ItemVersionRow.number, e.type, e.occurred_at, e.comment, e.reason)
            .join(ItemRow, ItemRow.id == e.item_id)
            .outerjoin(ItemVersionRow, ItemVersionRow.id == e.version_id)
            .where(e.actor_id == user_id)
            .order_by(e.occurred_at, e.id)
        )
        return [
            {
                "item": code,
                "version": number,
                "tipo": kind,
                "fecha": _iso(at),
                "comentario": comment,
                "motivo": reason,
            }
            for code, number, kind, at, comment, reason in rows
        ]

    async def _imports(self, user_id: UUID) -> list[dict[str, Any]]:
        rows = await self._db.scalars(
            select(ImportRow).where(ImportRow.created_by == user_id).order_by(ImportRow.created_at)
        )
        return [
            {
                "fecha": _iso(row.created_at),
                "formato": row.format,
                "estado": row.status,
                "confirmada": _iso(row.confirmed_at),
                "creados": (row.result or {}).get("created", 0),
                "versionados": (row.result or {}).get("versioned", 0),
            }
            for row in rows
        ]

    async def _exports(self, user_id: UUID) -> list[dict[str, Any]]:
        rows = await self._db.scalars(
            select(ExportRow).where(ExportRow.created_by == user_id).order_by(ExportRow.created_at)
        )
        return [
            {
                "fecha": _iso(row.created_at),
                "formato": row.format,
                "version": row.version_choice,
                "items": row.item_count,
                "omitidos": row.skipped_count,
            }
            for row in rows
        ]

    async def _taxonomy_changes(self, user_id: UUID) -> list[dict[str, Any]]:
        t = TaxonomyChangeRow
        rows = await self._db.execute(
            select(t.changed_at, t.target, t.action)
            .where(t.changed_by == user_id)
            .order_by(t.changed_at, t.id)
        )
        return [
            {"fecha": _iso(at), "objetivo": target, "accion": action} for at, target, action in rows
        ]
