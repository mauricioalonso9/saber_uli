"""Exportación del banco (US6; FR-038, SC-008, SC-010; research R-03, R-04 y R-18).

Escribe el banco, o lo que dejan los filtros, en el formato de importación: el JSON v1 o la
plantilla XLSX. De cada ítem va su versión publicada o, si se pide, la última. Lee la base por
bloques de 500 ítems, ordenados por código, y entrega el archivo por partes, sin cargarlo todo en
memoria. La plantilla, que necesita el total de omitidos en los encabezados, se arma completa
antes de responder.

El archivo incluye los contextos que usan sus ítems (en su versión vigente), los módulos con solo
las categorías que usan y las rúbricas de sus consignas, para poder reimportarlo en otra
instalación. Reimportar lo exportado no cambia nada (SC-008). Cada exportación terminada queda en
`content.exports`.
"""

from collections.abc import AsyncIterator, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from saber_uli.content.application.bundle import (
    Bundle,
    ContextSpec,
    ItemSpec,
    ModuleSpec,
    NodeSpec,
)
from saber_uli.content.application.ports import ExportedItem, ExportRecord, ItemFilters
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.context import Context
from saber_uli.content.domain.module import Module
from saber_uli.content.domain.rubric import Rubric
from saber_uli.content.domain.taxonomy import (
    ITEM_TAG_KINDS,
    TaxonomyNode,
    TaxonomyNodeKind,
    field_for,
)
from saber_uli.shared.domain.clock import Clock

__all__ = ["EXPORT_BATCH_SIZE", "BankExport", "ExportFile", "ExportRequest", "ExportWriter"]

EXPORT_BATCH_SIZE = 500
SCHEMA_VERSION = "1.0"

VersionChoice = Literal["published", "latest"]


@dataclass(frozen=True)
class ExportRequest:
    format: str
    version: VersionChoice = "published"
    module: str | None = None
    state: str | None = None
    origin: str | None = None
    difficulty: str | None = None
    taxonomy_node: UUID | None = None

    def applied_filters(self) -> dict[str, str]:
        """Los filtros que se usaron, para el registro (`content.exports.filter`)."""
        values = {
            "module": self.module,
            "state": self.state,
            "origin": self.origin,
            "difficulty": self.difficulty,
            "taxonomy_node": None if self.taxonomy_node is None else str(self.taxonomy_node),
        }
        return {name: value for name, value in values.items() if value is not None}


@dataclass
class ExportFile:
    filename: str
    media_type: str
    skipped: int
    chunks: AsyncIterator[bytes]


class ExportWriter(Protocol):
    """Un formato de exportación; una instancia por archivo."""

    media_type: str
    extension: str
    # True: entrega cada bloque al leerlo; False: el archivo sale completo al final.
    streams: bool

    def accepts(self, item: ItemSpec, context: ContextSpec | None) -> bool:
        """Si el formato puede representar el ítem (la plantilla no puede con todos)."""
        ...

    def begin(self) -> bytes: ...

    def items(self, entries: Sequence[tuple[ItemSpec, ContextSpec | None]]) -> bytes: ...

    def end(self, tail: Bundle) -> bytes:
        """Cierra el archivo con los contextos, módulos y rúbricas de `tail`."""
        ...


@dataclass
class _Progress:
    exported: int = 0
    skipped: int = 0
    nodes: set[UUID] = field(default_factory=set)
    rubrics: set[UUID] = field(default_factory=set)
    modules: set[str] = field(default_factory=set)
    contexts: dict[str, ContextSpec] = field(default_factory=dict)
    # Contextos ya leídos de la base, también los de ítems que el formato no representa.
    loaded: dict[str, ContextSpec | None] = field(default_factory=dict)


class _Catalog:
    """Traduce identificadores de categorías y rúbricas a los códigos del formato."""

    def __init__(
        self, modules: Iterable[Module], nodes: Iterable[TaxonomyNode], rubrics: Iterable[Rubric]
    ) -> None:
        self.modules = {module.code: module for module in modules}
        self.nodes = {node.id: node for node in nodes}
        self.rubrics = {rubric.id: rubric for rubric in rubrics if rubric.id is not None}

    def code(self, node_id: UUID | None) -> str | None:
        return None if node_id is None else self.nodes[node_id].code

    def ids(self, *codes: str | None) -> set[UUID]:
        wanted = set(codes) - {None}
        return {node.id for node in self.nodes.values() if node.code in wanted}

    def descendants(self, root: UUID) -> frozenset[UUID]:
        found = {root}
        changed = True
        while changed:
            changed = False
            for node in self.nodes.values():
                if node.parent_id in found and node.id not in found:
                    found.add(node.id)
                    changed = True
        return frozenset(found)

    def item_spec(self, entry: ExportedItem) -> ItemSpec:
        version = entry.version
        content = version.content
        tags: dict[TaxonomyNodeKind, str] = {}
        for kind in ITEM_TAG_KINDS:
            code = self.code(getattr(content.taxonomy, field_for(kind)))
            if code is not None:
                tags[kind] = code
        rubric = None if content.rubric_id is None else self.rubrics.get(content.rubric_id)
        return ItemSpec(
            code=entry.code,
            module_code=entry.module_code,
            kind=entry.kind,
            difficulty=content.difficulty,
            stem_md=content.stem_md,
            explanation_md=content.explanation_md,
            origin=entry.origin,
            tags=tags,
            options=content.options,
            answer_key=content.answer_key,
            prompt_context_md=content.prompt_context_md,
            rubric_code=None if rubric is None else rubric.code,
            context_code=content.context_code,
            state=version.state,
            version=version.number,
        )

    def context_spec(self, context: Context) -> ContextSpec:
        content = context.current.content
        return ContextSpec(
            code=context.code,
            module_code=context.module_code,
            kind=content.kind,
            title=content.title,
            origin=context.current.origin,
            body_md=content.body_md,
            media_id=content.media_id,
            alt_text=content.alt_text,
            text_type_code=self.code(content.text_type_node_id),
            part_code=self.code(content.part_node_id),
            subtype=content.subtype,
            shared_options=content.shared_options,
        )

    def module_specs(self, progress: _Progress) -> list[ModuleSpec]:
        """Los módulos exportados con solo las categorías que se usan (y sus ancestros)."""
        used: set[UUID] = set()
        for node_id in progress.nodes:
            current: UUID | None = node_id
            while current is not None and current not in used:
                used.add(current)
                current = self.nodes[current].parent_id
        specs = []
        for code in sorted(progress.modules):
            nodes = sorted(
                (self.nodes[i] for i in used if self.nodes[i].module_code == code),
                key=lambda node: (node.position, node.code),
            )
            specs.append(
                ModuleSpec(
                    module=self.modules[code],
                    nodes=tuple(
                        NodeSpec(
                            module_code=node.module_code,
                            kind=node.kind,
                            code=node.code,
                            name=node.name,
                            position=node.position,
                            description=node.description,
                            parent_code=self.code(node.parent_id),
                            target_weight=node.target_weight,
                            part_options=node.part_options,
                            part_format=node.part_format,
                        )
                        for node in nodes
                    ),
                )
            )
        return specs


class BankExport:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], ContentUnitOfWork],
        clock: Clock,
        writers: Mapping[str, Callable[[], ExportWriter]],
        batch_size: int = EXPORT_BATCH_SIZE,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._writers = writers
        self._batch_size = batch_size

    async def export(self, request: ExportRequest, actor: UUID) -> ExportFile:
        writer = self._writers[request.format]()
        now = self._clock.now()
        async with self._uow_factory() as uow:
            catalog = _Catalog(
                await uow.modules.list(), await uow.taxonomy.list(), await uow.rubrics.list()
            )
        filters = ItemFilters(
            module=request.module,
            state=request.state,
            origin=request.origin,
            difficulty=request.difficulty,
            taxonomy_ids=None
            if request.taxonomy_node is None
            else catalog.descendants(request.taxonomy_node),
        )
        progress = _Progress()
        chunks = self._generate(request, filters, catalog, writer, progress, actor, now)
        filename = f"banco-saber-uli-{now:%Y%m%d-%H%M}.{writer.extension}"
        if not writer.streams:
            content = b"".join([chunk async for chunk in chunks])
            chunks = _once(content)
        return ExportFile(filename, writer.media_type, progress.skipped, chunks)

    async def _generate(
        self,
        request: ExportRequest,
        filters: ItemFilters,
        catalog: _Catalog,
        writer: ExportWriter,
        progress: _Progress,
        actor: UUID,
        now: datetime,
    ) -> AsyncIterator[bytes]:
        yield writer.begin()
        after: str | None = None
        while True:
            async with self._uow_factory() as uow:
                batch = await uow.items.export_batch(
                    filters,
                    latest=request.version == "latest",
                    after=after,
                    limit=self._batch_size,
                )
                entries = await self._entries(uow, batch, catalog, writer, progress)
            if entries:
                yield writer.items(entries)
            if len(batch) < self._batch_size:
                break
            after = batch[-1].code
        tail = Bundle(
            schema_version=SCHEMA_VERSION,
            modules=catalog.module_specs(progress),
            contexts=[progress.contexts[code] for code in sorted(progress.contexts)],
            rubrics=[catalog.rubrics[i] for i in sorted(progress.rubrics, key=str)],
        )
        yield writer.end(tail)
        async with self._uow_factory() as uow:
            await uow.exports.add(
                ExportRecord(
                    created_by=actor,
                    created_at=now,
                    format=request.format,
                    filter=request.applied_filters(),
                    version_choice=request.version,
                    item_count=progress.exported,
                    skipped_count=progress.skipped,
                )
            )
            await uow.commit()

    async def _entries(
        self,
        uow: ContentUnitOfWork,
        batch: Sequence[ExportedItem],
        catalog: _Catalog,
        writer: ExportWriter,
        progress: _Progress,
    ) -> list[tuple[ItemSpec, ContextSpec | None]]:
        entries: list[tuple[ItemSpec, ContextSpec | None]] = []
        for entry in batch:
            spec = catalog.item_spec(entry)
            context = await _context(uow, spec.context_code, catalog, progress)
            if not writer.accepts(spec, context):
                progress.skipped += 1
                continue
            entries.append((spec, context))
            progress.exported += 1
            progress.modules.add(spec.module_code)
            taxonomy = entry.version.content.taxonomy
            progress.nodes |= {
                node_id
                for kind in ITEM_TAG_KINDS
                if (node_id := getattr(taxonomy, field_for(kind))) is not None
            }
            if entry.version.content.rubric_id is not None:
                progress.rubrics.add(entry.version.content.rubric_id)
            if context is not None:
                progress.contexts[context.code] = context
                progress.nodes |= catalog.ids(context.text_type_code, context.part_code)
        return entries


async def _context(
    uow: ContentUnitOfWork, code: str | None, catalog: _Catalog, progress: _Progress
) -> ContextSpec | None:
    if code is None:
        return None
    if code not in progress.loaded:
        stored = await uow.contexts.get_by_code(code)
        progress.loaded[code] = None if stored is None else catalog.context_spec(stored)
    return progress.loaded[code]


async def _once(content: bytes) -> AsyncIterator[bytes]:
    yield content
