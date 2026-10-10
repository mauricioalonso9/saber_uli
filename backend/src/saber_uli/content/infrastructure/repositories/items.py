"""Ítems, versiones e historia (data-model §2.6 a §2.8; ADR 0008).

Las versiones se escriben con sentencias explícitas y en orden: primero las que pasan a
`retired`, luego las demás actualizaciones y al final las nuevas. Así, al aprobar, la publicada
anterior deja de serlo antes de que la nueva lo sea y los índices únicos parciales (una publicada
y una abierta por ítem) nunca se violan a mitad de la operación.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, Uuid, and_, any_, case, func, insert, literal, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from saber_uli.content.application.ports import (
    CoverageCounts,
    ExportedItem,
    ImmutableVersionError,
    ItemFilters,
    ItemSummaryRow,
)
from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.events import HistoryEvent, HistoryEventType
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    ItemVersion,
    Option,
    VersionState,
)
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.content.infrastructure.orm import (
    ContextRow,
    ContextVersionRow,
    ItemEventRow,
    ItemRow,
    ItemVersionRow,
    ItemVersionStatsRow,
    TaxonomyNodeRow,
)
from saber_uli.shared.infrastructure.db import LIKE_ESCAPE, contains_pattern

_LOADED_STATES = ("published", "draft", "in_review")
_FINAL_STATES = ("published", "retired")


class SqlAlchemyItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, item: Item) -> Item:
        row = ItemRow(
            code=item.code,
            module_code=item.module_code,
            kind=item.kind.value,
            origin=item.origin.value,
            seed_hash=item.seed_hash,
            revision=item.revision,
        )
        if item.created_at is not None:
            row.created_at = item.created_at
        self._db.add(row)
        await self._db.flush()
        item.id = row.id
        for version in item.versions:
            await self._insert_version(row.id, version)
        await self._insert_events(row.id, item)
        return item

    async def save(self, item: Item) -> None:
        if item.id is None:
            raise ValueError("el ítem aún no se ha guardado; use add()")
        existing = [version for version in item.versions if version.id is not None]
        await self._check_immutable(existing)
        retiring = [v for v in existing if v.state is VersionState.RETIRED]
        others = [v for v in existing if v.state is not VersionState.RETIRED]
        for version in [*retiring, *others]:
            await self._db.execute(
                update(ItemVersionRow)
                .where(ItemVersionRow.id == version.id)
                .values(**_version_values(version))
            )
        for version in item.versions:
            if version.id is None:
                await self._insert_version(item.id, version)
        await self._db.execute(
            update(ItemRow)
            .where(ItemRow.id == item.id)
            .values(revision=item.revision, seed_hash=item.seed_hash)
        )
        await self._insert_events(item.id, item)

    async def get_by_code(self, code: str, *, for_update: bool = False) -> Item | None:
        query = select(ItemRow).where(ItemRow.code == code)
        if for_update:
            query = query.with_for_update()
        row = await self._db.scalar(query)
        if row is None:
            return None
        rows = await self._db.execute(
            select(ItemVersionRow, ContextRow.code)
            .outerjoin(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .outerjoin(ContextRow, ContextRow.id == ContextVersionRow.context_id)
            .where(ItemVersionRow.item_id == row.id, ItemVersionRow.state.in_(_LOADED_STATES))
            .order_by(ItemVersionRow.number)
        )
        last_number = await self._db.scalar(
            select(func.max(ItemVersionRow.number)).where(ItemVersionRow.item_id == row.id)
        )
        return Item(
            id=row.id,
            code=row.code,
            module_code=row.module_code,
            kind=ItemKind(row.kind),
            origin=Origin(row.origin),
            versions=[_version(version, context_code) for version, context_code in rows],
            last_number=int(last_number or 0),
            revision=row.revision,
            seed_hash=row.seed_hash,
            created_at=row.created_at,
        )

    async def code_with_fingerprint(
        self, fingerprint: bytes, *, excluding: UUID | None = None
    ) -> str | None:
        query = (
            select(ItemRow.code)
            .join(ItemVersionRow, ItemVersionRow.item_id == ItemRow.id)
            .where(ItemVersionRow.fingerprint == fingerprint, ItemVersionRow.state != "retired")
            .order_by(ItemRow.code)
            .limit(1)
        )
        if excluding is not None:
            query = query.where(ItemRow.id != excluding)
        code: str | None = await self._db.scalar(query)
        return code

    async def history(self, code: str) -> list[HistoryEvent]:
        rows = await self._db.execute(
            select(ItemEventRow, ItemVersionRow.number)
            .join(ItemRow, ItemRow.id == ItemEventRow.item_id)
            .outerjoin(ItemVersionRow, ItemVersionRow.id == ItemEventRow.version_id)
            .where(ItemRow.code == code)
            .order_by(ItemEventRow.occurred_at, ItemEventRow.id)
        )
        return [
            HistoryEvent(
                type=HistoryEventType(event.type),
                version_number=number,
                actor_id=event.actor_id,
                occurred_at=event.occurred_at,
                comment=event.comment,
                reason=event.reason,
                details=dict(event.details),
                id=event.id,
            )
            for event, number in rows
        ]

    async def codes_using_context(self, context_id: UUID) -> list[str]:
        rows = await self._db.scalars(
            select(ItemRow.code)
            .join(ItemVersionRow, ItemVersionRow.item_id == ItemRow.id)
            .join(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .where(
                ContextVersionRow.context_id == context_id,
                ItemVersionRow.state.in_(_LOADED_STATES),
            )
            .distinct()
            .order_by(ItemRow.code)
        )
        return list(rows)

    async def context_usage(self, context_id: UUID) -> list[tuple[str, str]]:
        rows = await self._db.execute(
            select(ItemRow.code, ItemVersionRow.state)
            .join(ItemVersionRow, ItemVersionRow.item_id == ItemRow.id)
            .join(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .where(
                ContextVersionRow.context_id == context_id,
                ItemVersionRow.state.in_(_LOADED_STATES),
            )
            .order_by(ItemRow.code)
        )
        return [(code, state) for code, state in rows]

    async def versions(self, code: str) -> list[ItemVersion]:
        rows = await self._db.execute(
            select(ItemVersionRow, ContextRow.code)
            .join(ItemRow, ItemRow.id == ItemVersionRow.item_id)
            .outerjoin(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .outerjoin(ContextRow, ContextRow.id == ContextVersionRow.context_id)
            .where(ItemRow.code == code)
            .order_by(ItemVersionRow.number)
        )
        return [_version(version, context_code) for version, context_code in rows]

    async def coverage_counts(self, module_code: str, tag: str) -> CoverageCounts:
        # Cada ítem tiene a lo sumo una versión publicada y una abierta: contar versiones es
        # contar ítems.
        node = getattr(ItemVersionRow, tag)
        rows = await self._db.execute(
            select(node, ItemVersionRow.state, func.count())
            .join(ItemRow, ItemRow.id == ItemVersionRow.item_id)
            .where(
                ItemRow.module_code == module_code,
                ItemVersionRow.state.in_(("published", "in_review")),
            )
            .group_by(node, ItemVersionRow.state)
        )
        totals = {"published": 0, "in_review": 0}
        by_node: dict[UUID, list[int]] = {}
        for node_id, state, count in rows:
            totals[state] += count
            if node_id is not None:
                by_node.setdefault(node_id, [0, 0])[0 if state == "published" else 1] += count
        return CoverageCounts(
            published_total=totals["published"],
            in_review_total=totals["in_review"],
            by_node={node_id: (p, r) for node_id, (p, r) in by_node.items()},
        )

    async def export_batch(
        self, filters: ItemFilters, *, latest: bool, after: str | None, limit: int
    ) -> list[ExportedItem]:
        if latest:
            chosen = (
                select(ItemVersionRow)
                .distinct(ItemVersionRow.item_id)
                .order_by(ItemVersionRow.item_id, ItemVersionRow.number.desc())
                .subquery("exported")
            )
        else:
            chosen = (
                select(ItemVersionRow)
                .where(ItemVersionRow.state == "published")
                .subquery("exported")
            )
        version = aliased(ItemVersionRow, chosen)
        query = (
            select(ItemRow, version, ContextRow.code)
            .join(version, version.item_id == ItemRow.id)
            .outerjoin(ContextVersionRow, ContextVersionRow.id == version.context_version_id)
            .outerjoin(ContextRow, ContextRow.id == ContextVersionRow.context_id)
            .order_by(ItemRow.code)
            .limit(limit)
        )
        if after is not None:
            query = query.where(ItemRow.code > after)
        if filters.module:
            query = query.where(ItemRow.module_code == filters.module)
        if filters.origin:
            query = query.where(ItemRow.origin == filters.origin)
        if filters.difficulty:
            query = query.where(version.difficulty == filters.difficulty)
        if filters.state:
            query = query.where(version.state == filters.state)
        if filters.taxonomy_ids is not None:
            ids = list(filters.taxonomy_ids)
            query = query.where(or_(*(column.in_(ids) for column in _tag_columns(version))))
        rows = await self._db.execute(query)
        return [
            ExportedItem(
                code=item.code,
                module_code=item.module_code,
                kind=ItemKind(item.kind),
                origin=Origin(item.origin),
                version=_version(row, context_code),
            )
            for item, row, context_code in rows
        ]

    async def count_matching_in_context(
        self, context_version_id: UUID, *, excluding: UUID | None
    ) -> int:
        same_context = select(ContextVersionRow.context_id).where(
            ContextVersionRow.id == context_version_id
        )
        query = (
            select(func.count(func.distinct(ItemRow.id)))
            .join(ItemVersionRow, ItemVersionRow.item_id == ItemRow.id)
            .join(ContextVersionRow, ContextVersionRow.id == ItemVersionRow.context_version_id)
            .where(
                ItemRow.kind == "matching",
                ItemVersionRow.state.in_(_LOADED_STATES),
                ContextVersionRow.context_id.in_(same_context.scalar_subquery()),
            )
        )
        if excluding is not None:
            query = query.where(ItemRow.id != excluding)
        return int(await self._db.scalar(query) or 0)

    async def search(
        self, filters: ItemFilters, *, offset: int, limit: int
    ) -> tuple[list[ItemSummaryRow], int]:
        query = _summary_query(filters)
        total = await self._db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self._db.execute(query.order_by(ItemRow.code).offset(offset).limit(limit))
        return [_summary(row) for row in rows], int(total or 0)

    # ------------------------------------------------------------------------ apoyo

    async def _check_immutable(self, versions: list[ItemVersion]) -> None:
        if not versions:
            return
        stored = await self._db.execute(
            select(ItemVersionRow.id, ItemVersionRow.state, ItemVersionRow.content_hash)
            .where(ItemVersionRow.id.in_([v.id for v in versions]))
            .with_for_update()
        )
        final = {
            version_id: content_hash
            for version_id, state, content_hash in stored
            if state in _FINAL_STATES
        }
        for version in versions:
            if version.id in final and version.content_hash != final[version.id]:
                raise ImmutableVersionError(
                    "El contenido de una versión publicada o retirada no se puede cambiar."
                )

    async def _insert_version(self, item_id: UUID, version: ItemVersion) -> None:
        new_id = await self._db.scalar(
            insert(ItemVersionRow)
            .values(item_id=item_id, number=version.number, **_version_values(version))
            .returning(ItemVersionRow.id)
        )
        version.id = new_id

    async def _insert_events(self, item_id: UUID, item: Item) -> None:
        events = item.pull_events()
        if not events:
            return
        ids = {version.number: version.id for version in item.versions}
        await self._db.execute(
            insert(ItemEventRow),
            [
                {
                    "item_id": item_id,
                    "version_id": ids.get(event.version_number)
                    if event.version_number is not None
                    else None,
                    "type": event.type.value,
                    "actor_id": event.actor_id,
                    "occurred_at": event.occurred_at,
                    "comment": event.comment,
                    "reason": event.reason,
                    "details": event.details,
                }
                for event in events
            ],
        )


def _tag_columns(version: Any) -> tuple[Any, ...]:
    return (
        version.competence_id,
        version.assertion_id,
        version.evidence_id,
        version.component_id,
        version.situation_id,
        version.part_id,
    )


def _version_values(version: ItemVersion) -> dict[str, Any]:
    content = version.content
    tags = content.taxonomy
    return {
        "state": version.state.value,
        "context_version_id": version.context_version_id,
        "difficulty": content.difficulty.value,
        "competence_id": tags.competence_id,
        "assertion_id": tags.assertion_id,
        "evidence_id": tags.evidence_id,
        "component_id": tags.component_id,
        "situation_id": tags.situation_id,
        "part_id": tags.part_id,
        "stem_md": content.stem_md,
        "options": None
        if content.options is None
        else [
            {"key": o.key, "text": o.text, "correct": o.correct, "feedback": o.feedback}
            for o in content.options
        ],
        "answer_key": content.answer_key,
        "explanation_md": content.explanation_md,
        "prompt_context_md": content.prompt_context_md,
        "rubric_id": content.rubric_id,
        "content_hash": version.content_hash,
        "fingerprint": version.fingerprint,
        "author_id": version.author_id,
        "contributor_ids": sorted(version.contributor_ids),
        "submitted_at": version.submitted_at,
        "submitted_by": version.submitted_by,
        "reviewed_at": version.reviewed_at,
        "reviewed_by": version.reviewed_by,
        "published_at": version.published_at,
        "retired_at": version.retired_at,
        "retired_by": version.retired_by,
        "retire_reason": version.retire_reason,
        "created_at": version.created_at,
        "updated_at": version.updated_at,
    }


def _version(row: ItemVersionRow, context_code: str | None) -> ItemVersion:
    return ItemVersion(
        id=row.id,
        number=row.number,
        state=VersionState(row.state),
        content=ItemContent(
            difficulty=Difficulty(row.difficulty),
            stem_md=row.stem_md,
            explanation_md=row.explanation_md,
            taxonomy=TaxonomyTags(
                competence_id=row.competence_id,
                assertion_id=row.assertion_id,
                evidence_id=row.evidence_id,
                component_id=row.component_id,
                situation_id=row.situation_id,
                part_id=row.part_id,
            ),
            options=None
            if row.options is None
            else tuple(
                Option(key=o["key"], text=o["text"], correct=o["correct"], feedback=o["feedback"])
                for o in row.options
            ),
            answer_key=row.answer_key,
            prompt_context_md=row.prompt_context_md,
            rubric_id=row.rubric_id,
            context_code=context_code,
        ),
        content_hash=row.content_hash,
        fingerprint=row.fingerprint,
        context_version_id=row.context_version_id,
        author_id=row.author_id,
        contributor_ids=frozenset(row.contributor_ids or ()),
        created_at=row.created_at,
        updated_at=row.updated_at,
        submitted_at=row.submitted_at,
        submitted_by=row.submitted_by,
        reviewed_at=row.reviewed_at,
        reviewed_by=row.reviewed_by,
        published_at=row.published_at,
        retired_at=row.retired_at,
        retired_by=row.retired_by,
        retire_reason=row.retire_reason,
    )


# ---------------------------------------------------------------------------- listado (SC-009)

_OPEN = ("draft", "in_review")


def _current_versions() -> Any:
    """Una versión por ítem para filtrar y resumir: la abierta, si no la publicada, si no la
    última (retirada)."""
    priority = case(
        (ItemVersionRow.state.in_(_OPEN), 0),
        (ItemVersionRow.state == "published", 1),
        else_=2,
    )
    return (
        select(ItemVersionRow)
        .distinct(ItemVersionRow.item_id)
        .order_by(ItemVersionRow.item_id, priority, ItemVersionRow.number.desc())
        .subquery("current_version")
    )


def _summary_query(filters: ItemFilters) -> Select[Any]:
    current = _current_versions()
    published = aliased(ItemVersionRow, name="published")
    open_ = aliased(ItemVersionRow, name="open_version")
    context_version = aliased(ContextVersionRow, name="context_version")
    context = aliased(ContextRow, name="context")
    assertion = aliased(TaxonomyNodeRow, name="assertion")
    part = aliased(TaxonomyNodeRow, name="part")
    query = (
        select(
            ItemRow.code,
            ItemRow.module_code,
            ItemRow.kind,
            ItemRow.origin,
            current.c.difficulty,
            current.c.stem_md,
            context.code.label("context_code"),
            assertion.code.label("assertion_code"),
            part.code.label("part_code"),
            published.number.label("published_number"),
            open_.number.label("open_number"),
            open_.state.label("open_state"),
            open_.author_id.label("open_author"),
            open_.contributor_ids.label("open_contributors"),
            ItemVersionStatsRow.signals,
            current.c.updated_at,
        )
        .join(current, current.c.item_id == ItemRow.id)
        .outerjoin(published, and_(published.item_id == ItemRow.id, published.state == "published"))
        .outerjoin(open_, and_(open_.item_id == ItemRow.id, open_.state.in_(_OPEN)))
        .outerjoin(context_version, context_version.id == current.c.context_version_id)
        .outerjoin(context, context.id == context_version.context_id)
        .outerjoin(assertion, assertion.id == current.c.assertion_id)
        .outerjoin(part, part.id == current.c.part_id)
        .outerjoin(ItemVersionStatsRow, ItemVersionStatsRow.version_id == published.id)
    )
    if filters.module:
        query = query.where(ItemRow.module_code == filters.module)
    if filters.origin:
        query = query.where(ItemRow.origin == filters.origin)
    if filters.difficulty:
        query = query.where(current.c.difficulty == filters.difficulty)
    if filters.state == "published":
        query = query.where(published.id.is_not(None))
    elif filters.state in _OPEN:
        query = query.where(open_.state == filters.state)
    elif filters.state == "retired":
        query = query.where(published.id.is_(None), open_.id.is_(None))
    if filters.taxonomy_ids is not None:
        ids = list(filters.taxonomy_ids)
        query = query.where(
            or_(
                *(
                    current.c[column].in_(ids)
                    for column in (
                        "competence_id",
                        "assertion_id",
                        "evidence_id",
                        "component_id",
                        "situation_id",
                        "part_id",
                    )
                )
            )
        )
    if filters.signal:
        query = query.where(ItemVersionStatsRow.signals.contains([filters.signal]))
    if filters.awaiting_review_of is not None:
        viewer = filters.awaiting_review_of
        query = query.where(
            open_.state == "in_review",
            or_(open_.author_id.is_(None), open_.author_id != viewer),
            ~(literal(viewer, Uuid) == any_(open_.contributor_ids)),
        )
    if filters.q:
        text = filters.q.strip()
        contains = contains_pattern(text)
        query = query.where(
            or_(
                func.lower(ItemRow.code).like(f"{contains[1:]}", escape=LIKE_ESCAPE),
                current.c.search.op("@@")(func.plainto_tsquery("spanish", text)),
                func.lower(context_version.title).like(contains, escape=LIKE_ESCAPE),
            )
        )
    return query


def _summary(row: Any) -> ItemSummaryRow:
    involved = frozenset(row.open_contributors or ()) | (
        frozenset({row.open_author}) if row.open_author is not None else frozenset()
    )
    return ItemSummaryRow(
        code=row.code,
        module=row.module_code,
        kind=row.kind,
        origin=row.origin,
        difficulty=row.difficulty,
        stem=row.stem_md,
        context_code=row.context_code,
        assertion_code=row.assertion_code,
        part_code=row.part_code,
        published_version=row.published_number,
        open_version=row.open_number,
        open_state=row.open_state,
        open_involved=involved,
        signals=tuple(row.signals or ()),
        updated_at=row.updated_at,
    )
