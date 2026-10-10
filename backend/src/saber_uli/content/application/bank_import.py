"""Importación en lote (US4 y US5; FR-028 a FR-037; research R-05).

1. **Vista previa** (`preview`): lee el archivo (JSON del banco o plantilla XLSX), resuelve los
   códigos contra la base y valida cada entrada con las mismas reglas del editor. Guarda una
   importación pendiente con el resultado de cada fila (nuevo, actualización con diferencias, sin
   cambios o error con sus motivos) y el contenido válido listo para aplicar. No guarda ítems.
2. **Confirmación** (`confirm`): con la declaración de originalidad (FR-036), aplica en una sola
   transacción los válidos (FR-034). Antes vuelve a evaluar: si otra persona creó o cambió un
   ítem después de la vista previa, ese ítem se omite (`changed_since_preview`).

La importación no cambia módulos, categorías ni rúbricas (los administra el administrador, US9):
esas secciones de un archivo del banco se ignoran. Nada entra publicado: los ítems nuevos y las
versiones nuevas entran en Borrador o En revisión, y los de origen IA siempre En revisión.
"""

import hashlib
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from saber_uli.content.application.bundle import (
    MAX_IMPORT_BYTES,
    MAX_IMPORT_ITEMS,
    BatchTooLargeError,
    Bundle,
    ContextSpec,
    EntryKind,
    ItemSpec,
    UnsupportedFileFormatError,
)
from saber_uli.content.application.context_changes import propagate_context_change
from saber_uli.content.application.ports import BundleCodec
from saber_uli.content.application.resolution import Resolver, context_text, item_hashes
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.application.validation import module_rules
from saber_uli.content.domain.context import (
    Context,
    ContextContent,
    ContextVersion,
    Origin,
    validate_context,
    word_count_for,
)
from saber_uli.content.domain.diff import FieldChange, diff_content
from saber_uli.content.domain.errors import FileTooLargeError, ItemNotFoundError
from saber_uli.content.domain.events import HistoryEventType
from saber_uli.content.domain.fingerprint import content_hash
from saber_uli.content.domain.import_job import (
    ImportAction,
    ImportJob,
    ImportNotPendingError,
    ImportRow,
    NothingToImportError,
)
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import ItemContent, ItemKind, VersionState, validate_item
from saber_uli.content.domain.taxonomy import TaxonomyNode
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.shared.domain.clock import Clock

__all__ = ["BankImport", "ImportNotPendingError", "NothingToImportError"]

R = ValidationRule
A = ImportAction
_ITEM_ENTITIES = (EntryKind.ITEM, EntryKind.WRITING_PROMPT)


@dataclass
class _ContextPlan:
    spec: ContextSpec
    content: ContextContent
    action: ImportAction
    revision: int | None


@dataclass
class _ItemPlan:
    spec: ItemSpec
    content: ItemContent
    action: ImportAction
    revision: int | None


@dataclass
class _Evaluation:
    rows: list[ImportRow] = field(default_factory=list)
    contexts: dict[str, _ContextPlan] = field(default_factory=dict)
    items: dict[str, _ItemPlan] = field(default_factory=dict)

    def bundle(self, schema_version: str) -> Bundle:
        """Las entradas que se aplicarían (nuevas o con cambios)."""
        return Bundle(
            schema_version=schema_version,
            contexts=[p.spec for p in self.contexts.values() if p.action is not A.UNCHANGED],
            items=[p.spec for p in self.items.values() if p.action is not A.UNCHANGED],
        )

    def expected(self) -> dict[str, dict[str, int | None]]:
        """Revisión de cada entrada al momento de la vista previa (`None`: no existía)."""
        return {
            "contexts": {code: plan.revision for code, plan in self.contexts.items()},
            "items": {code: plan.revision for code, plan in self.items.items()},
        }


def _entity(kind: ItemKind) -> str:
    return "writing_prompt" if kind is ItemKind.WRITING_PROMPT else "item"


def _context_changes(before: ContextContent, after: ContextContent) -> list[FieldChange]:
    changes = []
    for name in (f.name for f in fields(ContextContent)):
        old, new = getattr(before, name), getattr(after, name)
        if old != new:
            changes.append(FieldChange(name, _plain(old), _plain(new)))
    return changes


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, tuple):
        return [vars(option) for option in value]
    return str(getattr(value, "value", value))


class BankImport:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], ContentUnitOfWork],
        clock: Clock,
        readers: Mapping[str, Callable[[bytes], Bundle]],
        codec: BundleCodec,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._readers = readers
        self._codec = codec

    # ------------------------------------------------------------------------ vista previa

    async def preview(self, content: bytes, filename: str, actor: UUID) -> ImportJob:
        name = PurePosixPath(filename.replace("\\", "/")).name or "archivo"
        fmt = PurePosixPath(name).suffix.lower().lstrip(".")
        reader = self._readers.get(fmt)
        if reader is None:
            raise UnsupportedFileFormatError(
                "El archivo debe ser .json (banco) o .xlsx (plantilla)."
            )
        if len(content) > MAX_IMPORT_BYTES:
            raise FileTooLargeError("El archivo pesa más de 10 MB.")
        bundle = reader(content)
        entries = len(bundle.items) + sum(e.entity in _ITEM_ENTITIES for e in bundle.errors)
        if entries > MAX_IMPORT_ITEMS:
            raise BatchTooLargeError(f"El archivo tiene más de {MAX_IMPORT_ITEMS} ítems.")
        now = self._clock.now()
        async with self._uow_factory() as uow:
            evaluation = await _evaluate(uow, bundle, await _resolver(uow))
            job = ImportJob(
                id=None,
                created_by=actor,
                created_at=now,
                source_name=name,
                format=fmt,
                file_sha256=hashlib.sha256(content).digest(),
                rows=evaluation.rows,
                payload={
                    "bundle": self._codec.dump(evaluation.bundle(bundle.schema_version)),
                    "expected": evaluation.expected(),
                },
            )
            await uow.imports.add(job)
            await uow.commit()
        return job

    # ------------------------------------------------------------------------ consulta

    async def get(self, import_id: UUID, viewer: UUID, *, sees_all: bool) -> ImportJob:
        async with self._uow_factory() as uow:
            job = await uow.imports.get(import_id)
        if job is None or not (sees_all or job.created_by == viewer):
            raise ItemNotFoundError("La importación no existe.")
        return job

    async def list_imports(
        self, viewer: UUID, *, sees_all: bool, offset: int, limit: int
    ) -> tuple[list[ImportJob], int]:
        async with self._uow_factory() as uow:
            return await uow.imports.list(
                created_by=None if sees_all else viewer, offset=offset, limit=limit
            )

    async def active_nodes(self) -> list[TaxonomyNode]:
        """Categorías activas para las listas de la plantilla (research R-04)."""
        async with self._uow_factory() as uow:
            return [node for node in await uow.taxonomy.list() if node.active]

    async def purge_expired(self) -> int:
        async with self._uow_factory() as uow:
            expired = await uow.imports.expire_pending(self._clock.now())
            await uow.commit()
        return expired

    # ------------------------------------------------------------------------ confirmación

    async def confirm(
        self,
        import_id: UUID,
        actor: UUID,
        *,
        target_state: VersionState,
        originality_declared: bool,
    ) -> ImportJob:
        if not originality_declared or not target_state.is_open:
            raise ImportNotPendingError("Falta la declaración de originalidad.")
        now = self._clock.now()
        async with self._uow_factory() as uow:
            job = await uow.imports.get(import_id, for_update=True)
            if job is None or job.created_by != actor:
                raise ItemNotFoundError("La importación no existe.")
            if not job.is_pending(now) or job.payload is None:
                raise ImportNotPendingError("La importación ya se confirmó o venció.")
            counts = job.counts()
            if counts["create"] + counts["update"] == 0:
                raise NothingToImportError("La importación no tiene ítems válidos.")
            bundle = self._codec.load(job.payload["bundle"])
            expected: dict[str, dict[str, int | None]] = job.payload["expected"]
            evaluation = await _evaluate(uow, bundle, await _resolver(uow))
            skipped = _skipped(evaluation, expected)
            details = {"import_id": str(job.id)}
            file_items = frozenset(evaluation.items)
            for context_plan in evaluation.contexts.values():
                if context_plan.spec.code not in skipped:
                    await _apply_context(uow, context_plan, actor, now, file_items)
            created = versioned = 0
            for plan in evaluation.items.values():
                if plan.spec.code in skipped or plan.action is A.UNCHANGED:
                    continue
                state = VersionState.IN_REVIEW if plan.spec.origin is Origin.AI else target_state
                if await _apply_item(uow, plan, state, actor, now, details):
                    created += 1
                else:
                    versioned += 1
            job.confirm(
                target_state=target_state,
                now=now,
                created=created,
                versioned=versioned,
                skipped=sorted(code for code in skipped if code in evaluation.items),
            )
            await uow.imports.save(job)
            await uow.commit()
        return job


async def _resolver(uow: ContentUnitOfWork) -> Resolver:
    return Resolver(await uow.modules.list(), await uow.taxonomy.list(), await uow.rubrics.list())


def _skipped(evaluation: _Evaluation, expected: dict[str, dict[str, int | None]]) -> set[str]:
    """Entradas que cambiaron desde la vista previa (o que ya no son válidas)."""
    skipped: set[str] = set()
    for code, context_plan in evaluation.contexts.items():
        if expected["contexts"].get(code, -1) != context_plan.revision:
            skipped.add(code)
    for code, item_plan in evaluation.items.items():
        if expected["items"].get(code, -1) != item_plan.revision:
            skipped.add(code)
    for row in evaluation.rows:
        if row.action is A.ERROR and row.entity != "context":
            skipped.add(row.code)
    return skipped


# ---------------------------------------------------------------------------- evaluación


async def _evaluate(uow: ContentUnitOfWork, bundle: Bundle, resolver: Resolver) -> _Evaluation:
    evaluation = _Evaluation()
    for error in bundle.errors:
        if error.entity in (*_ITEM_ENTITIES, EntryKind.CONTEXT):
            evaluation.rows.append(
                ImportRow(error.code, error.entity.value, A.ERROR, errors=list(error.issues))
            )
    for context_spec in bundle.contexts:
        await _evaluate_context(uow, context_spec, resolver, evaluation)
    matching = Counter(s.context_code for s in bundle.items if s.kind is ItemKind.MATCHING)
    prints: dict[bytes, str] = {}
    for spec in bundle.items:
        siblings = matching[spec.context_code] - 1 if spec.kind is ItemKind.MATCHING else 0
        await _evaluate_item(uow, spec, resolver, evaluation, prints, siblings)
    return evaluation


async def _evaluate_context(
    uow: ContentUnitOfWork, spec: ContextSpec, resolver: Resolver, evaluation: _Evaluation
) -> None:
    content, issues = resolver.context_content(spec)
    rules = resolver.rules.get(spec.module_code)
    if rules is None:
        issues.append(ContentIssue("module", R.INVALID_VALUE, "El módulo no existe."))
    else:
        issues += validate_context(content, rules)
    if content.media_id is not None and await uow.media.get(content.media_id) is None:
        issues.append(ContentIssue("media_id", R.INVALID_VALUE, "La imagen no existe."))
    stored = await uow.contexts.get_by_code(spec.code)
    if stored is not None and stored.module_code != spec.module_code:
        issues.append(ContentIssue("module", R.INVALID_VALUE, "El contexto existe en otro módulo."))
    if issues:
        evaluation.rows.append(ImportRow(spec.code, "context", A.ERROR, errors=issues))
        return
    changes: list[FieldChange] = []
    if stored is None:
        action, revision = A.CREATE, None
    elif content_hash(content) == stored.current.content_hash:
        action, revision = A.UNCHANGED, stored.revision
    else:
        action = A.UPDATE
        changes = _context_changes(stored.current.content, content)
        revision = stored.revision
    evaluation.contexts[spec.code] = _ContextPlan(spec, content, action, revision)
    evaluation.rows.append(ImportRow(spec.code, "context", action, changes=changes))


async def _evaluate_item(
    uow: ContentUnitOfWork,
    spec: ItemSpec,
    resolver: Resolver,
    evaluation: _Evaluation,
    prints: dict[bytes, str],
    siblings: int,
) -> None:
    entity = _entity(spec.kind)
    content, issues = resolver.item_content(spec)
    stored = await uow.items.get_by_code(spec.code)
    context = await _context_for(uow, evaluation, content.context_code)
    rules = resolver.rules.get(spec.module_code)
    if rules is None:
        issues.append(ContentIssue("module", R.INVALID_VALUE, "El módulo no existe."))
    else:
        issues += validate_item(
            spec.kind, content, rules, context=context, matching_siblings=siblings
        )
    if stored is not None and (
        stored.module_code != spec.module_code or stored.kind is not spec.kind
    ):
        issues.append(
            ContentIssue("code", R.INVALID_VALUE, "El código ya existe con otro módulo o tipo.")
        )
    hash_, print_ = item_hashes(content, context_text(context))
    if not issues:
        if print_ in prints:
            issues.append(
                ContentIssue(
                    "stem_md",
                    R.DUPLICATE_IN_FILE,
                    f"El contenido coincide con el de {prints[print_]} en el mismo archivo.",
                )
            )
        else:
            duplicate = await uow.items.code_with_fingerprint(
                print_, excluding=None if stored is None else stored.id
            )
            if duplicate is not None:
                issues.append(
                    ContentIssue(
                        "stem_md",
                        R.DUPLICATE_ITEM,
                        f"El contenido coincide con el ítem {duplicate} del banco.",
                    )
                )
        prints.setdefault(print_, spec.code)
    if issues:
        evaluation.rows.append(ImportRow(spec.code, entity, A.ERROR, errors=issues))
        return
    target = "in_review" if spec.origin is Origin.AI else None
    changes: list[FieldChange] = []
    if stored is None:
        action, revision = A.CREATE, None
    else:
        # La versión vigente: la abierta, si no la publicada, si no la última (retirada, que el
        # agregado no carga).
        current = stored.open or stored.published or (await uow.items.versions(spec.code))[-1]
        revision = stored.revision
        changes = diff_content(current.content, content)
        # Un retirado vuelve con una versión nueva aunque el contenido sea igual; lo demás se
        # actualiza solo si cambió algún campo (FR-035).
        if current.state is VersionState.RETIRED or (current.content_hash != hash_ and changes):
            action = A.UPDATE
        else:
            action = A.UNCHANGED
    evaluation.items[spec.code] = _ItemPlan(spec, content, action, revision)
    evaluation.rows.append(
        ImportRow(spec.code, entity, action, target_state=target, changes=changes)
    )


async def _context_for(
    uow: ContentUnitOfWork, evaluation: _Evaluation, code: str | None
) -> ContextContent | None:
    if code is None:
        return None
    plan = evaluation.contexts.get(code)
    if plan is not None:
        return plan.content
    if any(row.code == code and row.entity == "context" for row in evaluation.rows):
        return None  # está en el archivo, pero con errores
    stored = await uow.contexts.get_by_code(code)
    return None if stored is None else stored.current.content


# ---------------------------------------------------------------------------- aplicación


async def _apply_context(
    uow: ContentUnitOfWork,
    plan: _ContextPlan,
    actor: UUID,
    now: datetime,
    file_items: frozenset[str],
) -> None:
    if plan.action is A.UNCHANGED:
        return
    rules = await _rules_words(uow, plan)
    if plan.action is A.CREATE:
        await uow.contexts.add(
            Context(
                id=None,
                code=plan.spec.code,
                module_code=plan.spec.module_code,
                current=_context_version(plan, 1, rules, actor, now),
            )
        )
        return
    stored = await uow.contexts.get_by_code(plan.spec.code, for_update=True)
    if stored is None:  # pragma: no cover - la evaluación lo acaba de ver
        return
    version = _context_version(plan, stored.current.number + 1, rules, actor, now)
    await uow.contexts.add_version(stored, version)
    await propagate_context_change(uow, stored, actor=actor, now=now, skip=file_items)


async def _rules_words(uow: ContentUnitOfWork, plan: _ContextPlan) -> int | None:
    rules = await module_rules(uow, plan.spec.module_code)
    return None if rules is None else word_count_for(plan.content, rules)


def _context_version(
    plan: _ContextPlan, number: int, words: int | None, actor: UUID, now: datetime
) -> ContextVersion:
    return ContextVersion(
        id=None,
        number=number,
        content=plan.content,
        word_count=words,
        origin=plan.spec.origin,
        content_hash=content_hash(plan.content),
        created_by=actor,
        created_at=now,
    )


async def _apply_item(
    uow: ContentUnitOfWork,
    plan: _ItemPlan,
    state: VersionState,
    actor: UUID,
    now: datetime,
    details: dict[str, Any],
) -> bool:
    """Aplica un ítem; `True` si es nuevo, `False` si recibió una versión."""
    context_version_id, text = None, None
    if plan.content.context_code is not None:
        context = await uow.contexts.get_by_code(plan.content.context_code)
        if context is not None:
            context_version_id = context.current.id
            text = context_text(context.current.content)
    hash_, print_ = item_hashes(plan.content, text)
    if plan.action is A.CREATE:
        await uow.items.add(
            Item.create(
                code=plan.spec.code,
                module_code=plan.spec.module_code,
                kind=plan.spec.kind,
                origin=plan.spec.origin,
                content=plan.content,
                content_hash=hash_,
                fingerprint=print_,
                context_version_id=context_version_id,
                actor=actor,
                now=now,
                state=state,
                event_type=HistoryEventType.IMPORTED,
                details=details,
            )
        )
        return True
    stored = await uow.items.get_by_code(plan.spec.code, for_update=True)
    if stored is None:  # pragma: no cover - la evaluación lo acaba de ver
        return False
    version = stored.edit(
        plan.content,
        hash_,
        print_,
        context_version_id,
        actor,
        now,
        keep_in_review=state is VersionState.IN_REVIEW,
        start_state=state,
        event_type=HistoryEventType.IMPORTED,
        details=details,
    )
    if state is VersionState.IN_REVIEW and version.state is VersionState.DRAFT:
        # Un Borrador actualizado entra a revisión si quien importa eligió ese estado (FR-016).
        stored.submit(actor, now)
    await uow.items.save(stored)
    return False
