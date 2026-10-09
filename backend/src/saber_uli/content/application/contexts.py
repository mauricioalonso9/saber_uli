"""Contextos compartidos (US3; FR-005, FR-007, FR-009, FR-020, FR-026).

Un contexto se guarda solo si es válido (palabras de Lectura crítica, texto alternativo, opciones
compartidas, categorías e imagen existentes). Editarlo crea una versión nueva y aplica FR-020 a
sus ítems (`context_changes.propagate_context_change`).
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from saber_uli.content.application.context_changes import (
    PropagationResult,
    propagate_context_change,
)
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
from saber_uli.content.domain.errors import (
    CodeTakenError,
    ContentValidationError,
    EditConflictError,
    ItemNotFoundError,
)
from saber_uli.content.domain.fingerprint import content_hash
from saber_uli.content.domain.module import ModuleRules
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.shared.domain.clock import Clock


@dataclass
class ContextDetails:
    context: Context
    item_count: int
    published_item_count: int
    items: list[tuple[str, str]]


class Contexts:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def create(
        self, *, code: str, module: str, content: ContextContent, actor: UUID
    ) -> Context:
        async with self._uow_factory() as uow:
            if await uow.contexts.get_by_code(code) is not None:
                raise CodeTakenError("Ya existe un contexto con ese código.")
            rules = await _rules(uow, module)
            words = await _validate(uow, rules, content)
            context = Context(
                id=None,
                code=code,
                module_code=module,
                current=_version(content, 1, words, actor, self._clock),
            )
            await uow.contexts.add(context)
            await uow.commit()
        return context

    async def update(
        self, code: str, content: ContextContent, actor: UUID, *, expected_revision: int
    ) -> tuple[Context, PropagationResult]:
        async with self._uow_factory() as uow:
            context = await uow.contexts.get_by_code(code, for_update=True)
            if context is None:
                raise ItemNotFoundError("El contexto no existe.")
            if context.revision != expected_revision:
                raise EditConflictError("Otra persona cambió este contexto mientras lo editabas.")
            rules = await _rules(uow, context.module_code)
            words = await _validate(uow, rules, content)
            version = _version(content, context.current.number + 1, words, actor, self._clock)
            await uow.contexts.add_version(context, version)
            result = await propagate_context_change(
                uow, context, actor=actor, now=self._clock.now()
            )
            await uow.commit()
        return context, result

    async def get(self, code: str) -> ContextDetails:
        async with self._uow_factory() as uow:
            context = await uow.contexts.get_by_code(code)
            if context is None or context.id is None:
                raise ItemNotFoundError("El contexto no existe.")
            usage = await uow.items.context_usage(context.id)
        published = {item for item, state in usage if state == "published"}
        current: dict[str, str] = {}
        for item, state in usage:
            if state != "published" or item not in current:
                current[item] = state
        return ContextDetails(
            context=context,
            item_count=len(current),
            published_item_count=len(published),
            items=sorted(current.items()),
        )


async def _rules(uow: ContentUnitOfWork, module: str) -> ModuleRules:
    rules = await module_rules(uow, module)
    if rules is None:
        raise ContentValidationError(
            [ContentIssue("module", ValidationRule.INVALID_VALUE, "El módulo no existe.")]
        )
    return rules


async def _validate(
    uow: ContentUnitOfWork, rules: ModuleRules, content: ContextContent
) -> int | None:
    issues = validate_context(content, rules)
    if content.media_id is not None and await uow.media.get(content.media_id) is None:
        issues.append(
            ContentIssue("media_id", ValidationRule.INVALID_VALUE, "La imagen no existe.")
        )
    if issues:
        raise ContentValidationError(issues)
    return word_count_for(content, rules)


def _version(
    content: ContextContent, number: int, words: int | None, actor: UUID, clock: Clock
) -> ContextVersion:
    return ContextVersion(
        id=None,
        number=number,
        content=content,
        word_count=words,
        origin=Origin.TEACHER,
        content_hash=content_hash(content),
        created_by=actor,
        created_at=clock.now(),
    )
