"""Contextos, sus versiones e imágenes (data-model §2.4 y §2.5)."""

from collections.abc import Collection
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.domain.context import (
    Context,
    ContextContent,
    ContextKind,
    ContextVersion,
    Origin,
    SharedOption,
)
from saber_uli.content.domain.media import Media
from saber_uli.content.infrastructure.orm import ContextRow, ContextVersionRow, MediaRow


class SqlAlchemyContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

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
