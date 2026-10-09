"""Consultas de ítems: detalle, listado e historia (contrato: `getItem`, `listItems`,
`getItemHistory`, `getItemVersion`).

Los nombres de autores y revisores los da la fachada de `identity` (research R-14). Las acciones
permitidas (`can`) dependen de los permisos de quien consulta y de la regla de autoaprobación
(FR-012, FR-013).
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from uuid import UUID

from saber_uli.content.application.ports import ItemFilters, ItemSummaryRow, UserNames
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.application.validation import module_rules, version_issues
from saber_uli.content.domain.diff import FieldChange, diff_content
from saber_uli.content.domain.errors import ItemNotFoundError
from saber_uli.content.domain.events import HistoryEvent, HistoryEventType
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import ItemVersion, VersionState
from saber_uli.content.domain.taxonomy import TaxonomyNode
from saber_uli.content.domain.validation import ContentIssue

AUTHOR = "content:author"
REVIEW = "content:review"


@dataclass(frozen=True)
class Viewer:
    id: UUID
    permissions: frozenset[str]


@dataclass
class ItemDetails:
    item: Item
    open_issues: list[ContentIssue]
    context_numbers: dict[UUID, int]
    names: dict[UUID, str]
    last_review_comment: str | None
    can: dict[str, bool]
    approve_blocked_reason: str | None


def _people(versions: Iterable[ItemVersion]) -> set[UUID]:
    ids: set[UUID] = set()
    for version in versions:
        ids |= set(version.contributor_ids)
        ids |= {p for p in (version.author_id, version.reviewed_by) if p is not None}
    return ids


class GetItem:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], names: UserNames) -> None:
        self._uow_factory = uow_factory
        self._names = names

    async def execute(self, code: str, viewer: Viewer) -> ItemDetails:
        async with self._uow_factory() as uow:
            item = await uow.items.get_by_code(code)
            if item is None:
                raise ItemNotFoundError("El ítem no existe.")
            issues: list[ContentIssue] = []
            if item.open is not None:
                rules = await module_rules(uow, item.module_code)
                if rules is not None:
                    issues = await version_issues(uow, rules, item, item.open)
            numbers = await uow.contexts.version_numbers(
                [v.context_version_id for v in item.versions if v.context_version_id]
            )
            history = await uow.items.history(code)
        names = await self._names.display_names(_people(item.versions))
        last_comment = None
        if item.open is not None and item.open.state is VersionState.DRAFT:
            returned = [e for e in history if e.type is HistoryEventType.RETURNED]
            last_comment = returned[-1].comment if returned else None
        can, blocked = _can(item, viewer)
        return ItemDetails(item, issues, numbers, names, last_comment, can, blocked)


def _can(item: Item, viewer: Viewer) -> tuple[dict[str, bool], str | None]:
    author = AUTHOR in viewer.permissions
    reviewer = REVIEW in viewer.permissions
    version = item.open
    in_review = version is not None and version.state is VersionState.IN_REVIEW
    involved = version is not None and version.involves(viewer.id)
    can = {
        "edit": author,
        "submit": author and version is not None and version.state is VersionState.DRAFT,
        "approve": reviewer and in_review and not involved,
        "return": reviewer and in_review,
        "reject": reviewer and in_review,
        "retire": reviewer and item.published is not None,
    }
    blocked = "self_approval" if reviewer and in_review and involved else None
    return can, blocked


# ------------------------------------------------------------------------------- listado


@dataclass
class ItemSummary:
    row: ItemSummaryRow
    needs_another_reviewer: bool


@dataclass
class ItemPage:
    items: list[ItemSummary]
    total: int


class ListItems:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], names: UserNames) -> None:
        self._uow_factory = uow_factory
        self._names = names

    async def execute(
        self,
        filters: ItemFilters,
        *,
        taxonomy_node: UUID | None,
        offset: int,
        limit: int,
    ) -> ItemPage:
        async with self._uow_factory() as uow:
            if taxonomy_node is not None:
                nodes = await uow.taxonomy.list()
                filters = _with_descendants(filters, taxonomy_node, nodes)
            rows, total = await uow.items.search(filters, offset=offset, limit=limit)
        admins = await self._names.active_admin_ids()
        return ItemPage(
            items=[
                ItemSummary(
                    row=row,
                    needs_another_reviewer=row.open_state == "in_review"
                    and bool(admins)
                    and admins <= row.open_involved,
                )
                for row in rows
            ],
            total=total,
        )


def _with_descendants(filters: ItemFilters, root: UUID, nodes: list[TaxonomyNode]) -> ItemFilters:
    children: dict[UUID, list[UUID]] = {}
    for node in nodes:
        if node.parent_id is not None:
            children.setdefault(node.parent_id, []).append(node.id)
    found = {root}
    pending = [root]
    while pending:
        for child in children.get(pending.pop(), []):
            if child not in found:
                found.add(child)
                pending.append(child)
    from dataclasses import replace

    return replace(filters, taxonomy_ids=frozenset(found))


# ------------------------------------------------------------------------------- historia


@dataclass
class VersionHistory:
    version: ItemVersion
    changed_fields: list[str]


@dataclass
class ItemHistory:
    versions: list[VersionHistory]
    events: list[HistoryEvent]
    names: dict[UUID, str] = field(default_factory=dict)


@dataclass
class VersionDetails:
    item: Item
    version: ItemVersion
    changes: list[FieldChange]
    issues: list[ContentIssue]
    context_numbers: dict[UUID, int]
    names: dict[UUID, str]


class ItemHistoryQuery:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], names: UserNames) -> None:
        self._uow_factory = uow_factory
        self._names = names

    async def history(self, code: str) -> ItemHistory:
        async with self._uow_factory() as uow:
            versions = await uow.items.versions(code)
            if not versions:
                raise ItemNotFoundError("El ítem no existe.")
            events = await uow.items.history(code)
        people = _people(versions) | {e.actor_id for e in events if e.actor_id is not None}
        names = await self._names.display_names(people)
        out = []
        previous = None
        for version in versions:
            changes = diff_content(None if previous is None else previous.content, version.content)
            out.append(VersionHistory(version, [change.field for change in changes]))
            previous = version
        return ItemHistory(out, events, names)

    async def version(self, code: str, number: int) -> VersionDetails:
        async with self._uow_factory() as uow:
            item = await uow.items.get_by_code(code)
            versions = await uow.items.versions(code)
            current = next((v for v in versions if v.number == number), None)
            if item is None or current is None:
                raise ItemNotFoundError("La versión no existe.")
            previous = next((v for v in versions if v.number == number - 1), None)
            issues: list[ContentIssue] = []
            rules = await module_rules(uow, item.module_code)
            if rules is not None:
                issues = await version_issues(uow, rules, item, current)
            numbers = await uow.contexts.version_numbers(
                [current.context_version_id] if current.context_version_id else []
            )
        names = await self._names.display_names(_people([current]))
        changes = diff_content(None if previous is None else previous.content, current.content)
        return VersionDetails(item, current, changes, issues, numbers, names)
