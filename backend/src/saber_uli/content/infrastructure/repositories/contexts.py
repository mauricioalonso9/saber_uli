"""Contextos, sus versiones e imágenes (data-model §2.4 y §2.5)."""

from collections.abc import Collection
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from saber_uli.content.application.ports import ContextSummaryRow
from saber_uli.content.domain.context import (
    Context,
    ContextContent,
    ContextKind,
    ContextVersion,
    Origin,
    SharedOption,
)
from saber_uli.content.domain.media import Media
from saber_uli.content.infrastructure.orm import (
    ContextRow,
    ContextVersionRow,
    ItemVersionRow,
    MediaRow,
)
from saber_uli.shared.infrastructure.db import LIKE_ESCAPE, contains_pattern


class SqlAlchemyContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def search(
        self, *, module: str | None, q: str | None, offset: int, limit: int
    ) -> tuple[list[ContextSummaryRow], int]:
        used = ItemVersionRow.state.in_(("published", "draft", "in_review"))
        usage = (
            select(
                ContextVersionRow.context_id,
                func.count(distinct(ItemVersionRow.item_id)).label("item_total"),
                func.count(distinct(ItemVersionRow.item_id))
                .filter(ItemVersionRow.state == "published")
                .label("published"),
            )
            .join(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .where(used)
            .group_by(ContextVersionRow.context_id)
            .subquery("usage")
        )
        current = aliased(ContextVersionRow, name="current_version")
        conditions = []
        if module:
            conditions.append(ContextRow.module_code == module)
        if q:
            pattern = contains_pattern(q)
            conditions.append(
                or_(
                    func.lower(ContextRow.code).like(pattern, escape=LIKE_ESCAPE),
                    func.lower(current.title).like(pattern, escape=LIKE_ESCAPE),
                )
            )
        base = select(ContextRow.id).join(current, current.id == ContextRow.current_version_id)
        total = await self._db.scalar(
            select(func.count()).select_from(base.where(*conditions).subquery())
        )
        rows = await self._db.execute(
            select(
                ContextRow.code,
                ContextRow.module_code,
                current.kind,
                current.title,
                current.number,
                current.word_count,
                func.coalesce(usage.c.item_total, 0),
                func.coalesce(usage.c.published, 0),
            )
            .join(current, current.id == ContextRow.current_version_id)
            .outerjoin(usage, usage.c.context_id == ContextRow.id)
            .where(*conditions)
            .order_by(ContextRow.code)
            .offset(offset)
            .limit(limit)
        )
        return [ContextSummaryRow(*row) for row in rows], int(total or 0)

    async def add(self, context: Context) -> Context:
        row = ContextRow(
            code=context.code,
            module_code=context.module_code,
            seed_hash=context.seed_hash,
            revision=context.revision,
        )
        self._db.add(row)
        await self._db.flush()
        context.id = row.id
        await self._insert_version(row.id, context.current)
        row.current_version_id = context.current.id
        await self._db.flush()
        return context

    async def add_version(self, context: Context, version: ContextVersion) -> None:
        if context.id is None:
            raise ValueError("el contexto aún no se ha guardado; use add()")
        await self._insert_version(context.id, version)
        context.revision += 1
        await self._db.execute(
            update(ContextRow)
            .where(ContextRow.id == context.id)
            .values(
                current_version_id=version.id,
                revision=context.revision,
                seed_hash=context.seed_hash,
            )
        )
        context.current = version

    async def get_by_code(self, code: str, *, for_update: bool = False) -> Context | None:
        query = select(ContextRow).where(ContextRow.code == code)
        if for_update:
            query = query.with_for_update()
        row = await self._db.scalar(query)
        if row is None or row.current_version_id is None:
            return None
        version = await self._db.get(ContextVersionRow, row.current_version_id)
        if version is None:  # pragma: no cover - la FK lo impide
            return None
        return Context(
            id=row.id,
            code=row.code,
            module_code=row.module_code,
            current=_version(version),
            revision=row.revision,
            seed_hash=row.seed_hash,
        )

    async def get_version(self, version_id: UUID) -> ContextVersion | None:
        row = await self._db.get(ContextVersionRow, version_id)
        return None if row is None else _version(row)

    async def codes_by_version(self, version_ids: Collection[UUID]) -> dict[UUID, str]:
        if not version_ids:
            return {}
        rows = await self._db.execute(
            select(ContextVersionRow.id, ContextRow.code)
            .join(ContextRow, ContextRow.id == ContextVersionRow.context_id)
            .where(ContextVersionRow.id.in_(list(version_ids)))
        )
        return dict(rows.tuples().all())

    async def version_numbers(self, version_ids: Collection[UUID]) -> dict[UUID, int]:
        if not version_ids:
            return {}
        rows = await self._db.execute(
            select(ContextVersionRow.id, ContextVersionRow.number).where(
                ContextVersionRow.id.in_(list(version_ids))
            )
        )
        return dict(rows.tuples().all())

    async def _insert_version(self, context_id: UUID, version: ContextVersion) -> None:
        content = version.content
        row = ContextVersionRow(
            context_id=context_id,
            number=version.number,
            kind=content.kind.value,
            title=content.title,
            body_md=content.body_md,
            media_id=content.media_id,
            alt_text=content.alt_text,
            text_type_node_id=content.text_type_node_id,
            part_node_id=content.part_node_id,
            subtype=content.subtype,
            shared_options=_options_to_json(content.shared_options),
            word_count=version.word_count,
            origin=version.origin.value,
            content_hash=version.content_hash,
            created_by=version.created_by,
            created_at=version.created_at,
        )
        self._db.add(row)
        await self._db.flush()
        version.id = row.id


def _options_to_json(options: tuple[SharedOption, ...] | None) -> list[dict[str, Any]] | None:
    if options is None:
        return None
    return [{"key": o.key, "text": o.text, "feedback": o.feedback} for o in options]


def _version(row: ContextVersionRow) -> ContextVersion:
    shared = (
        None
        if row.shared_options is None
        else tuple(
            SharedOption(key=o["key"], text=o["text"], feedback=o["feedback"])
            for o in row.shared_options
        )
    )
    return ContextVersion(
        id=row.id,
        number=row.number,
        content=ContextContent(
            kind=ContextKind(row.kind),
            title=row.title,
            body_md=row.body_md,
            media_id=row.media_id,
            alt_text=row.alt_text,
            text_type_node_id=row.text_type_node_id,
            part_node_id=row.part_node_id,
            subtype=row.subtype,
            shared_options=shared,
        ),
        word_count=row.word_count,
        origin=Origin(row.origin),
        content_hash=row.content_hash,
        created_by=row.created_by,
        created_at=row.created_at,
    )


class SqlAlchemyMediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, media: Media) -> Media:
        row = MediaRow(
            sha256=media.sha256,
            content_type=media.content_type,
            width=media.width,
            height=media.height,
            size_bytes=media.size_bytes,
            data=media.data,
            created_by=media.created_by,
            created_at=media.created_at,
        )
        self._db.add(row)
        await self._db.flush()
        return _media(row)

    async def get(self, media_id: UUID) -> Media | None:
        row = await self._db.get(MediaRow, media_id)
        return None if row is None else _media(row)

    async def get_by_sha256(self, sha256: bytes) -> Media | None:
        row = await self._db.scalar(select(MediaRow).where(MediaRow.sha256 == sha256))
        return None if row is None else _media(row)

    async def add_or_get(self, media: Media) -> Media:
        # ON CONFLICT: dos subidas simultáneas de la misma imagen no chocan con la llave única.
        await self._db.execute(
            insert(MediaRow)
            .values(
                sha256=media.sha256,
                content_type=media.content_type,
                width=media.width,
                height=media.height,
                size_bytes=media.size_bytes,
                data=media.data,
                created_by=media.created_by,
                created_at=media.created_at,
            )
            .on_conflict_do_nothing(constraint="uq_media_sha256")
        )
        stored = await self.get_by_sha256(media.sha256)
        if stored is None:  # pragma: no cover - la fila existe tras el INSERT
            raise RuntimeError("la imagen no quedó guardada")
        return stored

    async def is_public(self, media_id: UUID) -> bool:
        visible = (
            select(ItemVersionRow.id)
            .join(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .where(
                ContextVersionRow.media_id == media_id,
                ItemVersionRow.state.in_(("published", "retired")),
            )
            .exists()
        )
        return bool(await self._db.scalar(select(visible)))


def _media(row: MediaRow) -> Media:
    return Media(
        id=row.id,
        sha256=row.sha256,
        content_type=row.content_type,
        width=row.width,
        height=row.height,
        size_bytes=row.size_bytes,
        data=row.data,
        created_by=row.created_by,
        created_at=row.created_at,
    )
