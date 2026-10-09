"""Carga del banco inicial en cada despliegue (US1; FR-021 a FR-023; research R-07; ADR 0008).

1. Lee el archivo y valida **todo** (forma, códigos y reglas de cada módulo). Con un solo
   problema lanza `SeedInvalidError` y no aplica nada (FR-023).
2. En una transacción con *advisory lock* (dos despliegues no cargan a la vez):
   - agrega módulos, categorías y rúbricas nuevos; los existentes no se tocan (los mantiene el
     administrador, US9);
   - contextos e ítems por `seed_hash` (huella de la entrada en el archivo):
     - código nuevo: entra En revisión, sin autor (el sistema);
     - mismo `seed_hash`: no se toca, aunque un docente lo haya cambiado (FR-022);
     - `seed_hash` distinto: versión nueva En revisión, o se actualiza la versión abierta que
       dejó la carga si nadie la tocó;
     - `seed_hash` distinto y una versión abierta hecha por personas: no se aplica y queda en
       `pending_manual` (FR-022a).
3. Registra la carga en `content.seed_loads`.

El banco inicial nunca publica: un ítem marcado "publicado" o "retirado" entra En revisión
(constitución VI: revisión humana antes de publicar).
"""

import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID, uuid4

import structlog

from saber_uli.content.application.bundle import Bundle, ContextSpec, NodeSpec
from saber_uli.content.application.context_changes import propagate_context_change
from saber_uli.content.application.ports import SeedLoadRecord
from saber_uli.content.application.resolution import Resolver, context_text, item_hashes
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.context import (
    Context,
    ContextContent,
    ContextVersion,
    validate_context,
    word_count_for,
)
from saber_uli.content.domain.events import HistoryEventType
from saber_uli.content.domain.fingerprint import content_hash
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import (
    ItemContent,
    ItemKind,
    ItemVersion,
    VersionState,
    validate_item,
)
from saber_uli.content.domain.taxonomy import TaxonomyNode
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import RuleViolationError

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SeedProblem:
    code: str
    rule: ValidationRule
    field: str


class SeedInvalidError(RuleViolationError):
    slug = "seed-invalid"

    def __init__(self, problems: list[SeedProblem]) -> None:
        super().__init__(f"El banco inicial tiene {len(problems)} problemas; no se aplicó nada.")
        self.problems = problems


@dataclass
class SeedLoadResult:
    added_modules: int = 0
    added_nodes: int = 0
    added_rubrics: int = 0
    added_contexts: int = 0
    versioned_contexts: int = 0
    unchanged_contexts: int = 0
    added_items: int = 0
    versioned_items: int = 0
    unchanged_items: int = 0
    pending_manual: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        counts = {key: value for key, value in vars(self).items() if isinstance(value, int)}
        return counts | {"pending_manual": len(self.pending_manual)}


def _seed_state(state: VersionState | None) -> VersionState:
    return VersionState.DRAFT if state is VersionState.DRAFT else VersionState.IN_REVIEW


def _edited_by_people(version: ItemVersion | None) -> bool:
    return version is not None and (version.author_id is not None or bool(version.contributor_ids))


class SeedLoader:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], ContentUnitOfWork],
        clock: Clock,
        reader: Callable[[bytes], Bundle],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._reader = reader

    async def execute(self, content: bytes) -> SeedLoadResult:
        bundle = self._reader(content)
        problems = [
            SeedProblem(error.code, issue.rule, issue.field)
            for error in bundle.errors
            for issue in error.issues
        ]
        if problems:
            raise SeedInvalidError(problems)
        now = self._clock.now()
        result = SeedLoadResult()
        async with self._uow_factory() as uow:
            await uow.lock_seed()
            resolver = await self._catalog(uow, bundle, result)
            contexts = await self._validate(uow, bundle, resolver)
            await self._apply_contexts(uow, bundle, resolver, contexts, result, now)
            await self._apply_items(uow, bundle, resolver, result, now)
            await uow.seed_loads.add(
                SeedLoadRecord(
                    loaded_at=now,
                    file_sha256=hashlib.sha256(content).digest(),
                    schema_version=bundle.schema_version,
                    summary=result.summary(),
                    pending_manual=result.pending_manual,
                )
            )
            await uow.commit()
        return result

    # ------------------------------------------------------------------------ catálogo

    async def _catalog(
        self, uow: ContentUnitOfWork, bundle: Bundle, result: SeedLoadResult
    ) -> Resolver:
        modules = {module.code: module for module in await uow.modules.list()}
        for spec in bundle.modules:
            if spec.module.code not in modules:
                await uow.modules.add(spec.module)
                modules[spec.module.code] = spec.module
                result.added_modules += 1
        nodes = {node.code: node for node in await uow.taxonomy.list()}
        for node_spec in (node for module in bundle.modules for node in module.nodes):
            if node_spec.code not in nodes:
                nodes[node_spec.code] = await uow.taxonomy.add(_node(node_spec, nodes))
                result.added_nodes += 1
        rubrics = {rubric.code: rubric for rubric in await uow.rubrics.list()}
        for rubric in bundle.rubrics:
            if rubric.code not in rubrics:
                rubrics[rubric.code] = await uow.rubrics.add(rubric)
                result.added_rubrics += 1
        return Resolver(modules.values(), nodes.values(), rubrics.values())

    # ------------------------------------------------------------------------ validación

    async def _validate(
        self, uow: ContentUnitOfWork, bundle: Bundle, resolver: Resolver
    ) -> dict[str, ContextContent]:
        problems: list[SeedProblem] = []
        contexts: dict[str, ContextContent] = {}
        for spec in bundle.contexts:
            content, issues = resolver.context_content(spec)
            rules = resolver.rules.get(spec.module_code)
            if rules is not None:
                issues += validate_context(content, rules)
            contexts[spec.code] = content
            problems += [SeedProblem(spec.code, i.rule, i.field) for i in issues]
        matching = Counter(
            spec.context_code for spec in bundle.items if spec.kind is ItemKind.MATCHING
        )
        for item_spec in bundle.items:
            item_content, issues = resolver.item_content(item_spec)
            context = await self._context_content(uow, contexts, item_spec.context_code)
            rules = resolver.rules.get(item_spec.module_code)
            if rules is not None:
                siblings = (
                    matching[item_spec.context_code] - 1
                    if item_spec.kind is ItemKind.MATCHING
                    else 0
                )
                issues += validate_item(
                    item_spec.kind,
                    item_content,
                    rules,
                    context=context,
                    matching_siblings=siblings,
                )
            problems += [SeedProblem(item_spec.code, i.rule, i.field) for i in issues]
        if problems:
            raise SeedInvalidError(problems)
        return contexts

    @staticmethod
    async def _context_content(
        uow: ContentUnitOfWork, contexts: dict[str, ContextContent], code: str | None
    ) -> ContextContent | None:
        if code is None:
            return None
        if code in contexts:
            return contexts[code]
        stored = await uow.contexts.get_by_code(code)
        return None if stored is None else stored.current.content

    # ------------------------------------------------------------------------ contextos

    async def _apply_contexts(
        self,
        uow: ContentUnitOfWork,
        bundle: Bundle,
        resolver: Resolver,
        contents: dict[str, ContextContent],
        result: SeedLoadResult,
        now: datetime,
    ) -> None:
        item_codes = frozenset(spec.code for spec in bundle.items)
        for spec in bundle.contexts:
            seed_hash = content_hash(replace(spec, state=None))
            content = contents[spec.code]
            rules = resolver.rules.get(spec.module_code)
            words = None if rules is None else word_count_for(content, rules)
            stored = await uow.contexts.get_by_code(spec.code, for_update=True)
            if stored is None:
                await uow.contexts.add(
                    Context(
                        id=None,
                        code=spec.code,
                        module_code=spec.module_code,
                        current=_context_version(spec, content, 1, words, now),
                        seed_hash=seed_hash,
                    )
                )
                result.added_contexts += 1
            elif stored.seed_hash == seed_hash:
                result.unchanged_contexts += 1
            elif stored.current.created_by is not None:
                result.pending_manual.append(spec.code)
            else:
                stored.seed_hash = seed_hash
                version = _context_version(spec, content, stored.current.number + 1, words, now)
                await uow.contexts.add_version(stored, version)
                await propagate_context_change(uow, stored, actor=None, now=now, skip=item_codes)
                result.versioned_contexts += 1

    # ------------------------------------------------------------------------ ítems

    async def _apply_items(
        self,
        uow: ContentUnitOfWork,
        bundle: Bundle,
        resolver: Resolver,
        result: SeedLoadResult,
        now: datetime,
    ) -> None:
        for spec in bundle.items:
            seed_hash = content_hash(replace(spec, state=None, version=None))
            content, _ = resolver.item_content(spec)
            context_version_id, text = await _context_of(uow, content)
            hash_, print_ = item_hashes(content, text)
            stored = await uow.items.get_by_code(spec.code, for_update=True)
            if stored is None:
                item = Item.create(
                    code=spec.code,
                    module_code=spec.module_code,
                    kind=spec.kind,
                    origin=spec.origin,
                    content=content,
                    content_hash=hash_,
                    fingerprint=print_,
                    context_version_id=context_version_id,
                    actor=None,
                    now=now,
                    state=_seed_state(spec.state),
                    event_type=HistoryEventType.SEED_LOADED,
                )
                item.seed_hash = seed_hash
                await uow.items.add(item)
                result.added_items += 1
            elif stored.seed_hash == seed_hash:
                result.unchanged_items += 1
            elif _edited_by_people(stored.open):
                result.pending_manual.append(spec.code)
            else:
                stored.edit(
                    content,
                    hash_,
                    print_,
                    context_version_id,
                    None,
                    now,
                    keep_in_review=True,
                    start_state=_seed_state(spec.state),
                    event_type=HistoryEventType.SEED_VERSIONED,
                )
                stored.seed_hash = seed_hash
                await uow.items.save(stored)
                result.versioned_items += 1


def _node(spec: NodeSpec, nodes: dict[str, TaxonomyNode]) -> TaxonomyNode:
    parent = None if spec.parent_code is None else nodes.get(spec.parent_code)
    return TaxonomyNode(
        id=uuid4(),
        module_code=spec.module_code,
        kind=spec.kind,
        code=spec.code,
        name=spec.name,
        position=spec.position,
        description=spec.description,
        parent_id=None if parent is None else parent.id,
        target_weight=spec.target_weight,
        part_options=spec.part_options,
        part_format=spec.part_format,
    )


def _context_version(
    spec: ContextSpec, content: ContextContent, number: int, words: int | None, now: datetime
) -> ContextVersion:
    return ContextVersion(
        id=None,
        number=number,
        content=content,
        word_count=words,
        origin=spec.origin,
        content_hash=content_hash(content),
        created_by=None,
        created_at=now,
    )


async def _context_of(
    uow: ContentUnitOfWork, content: ItemContent
) -> tuple[UUID | None, str | None]:
    if content.context_code is None:
        return None, None
    context = await uow.contexts.get_by_code(content.context_code)
    if context is None:  # pragma: no cover - la validación lo impide
        return None, None
    return context.current.id, context_text(context.current.content)
