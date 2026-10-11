"""Creación y edición de ítems por docentes y administradores (US3; FR-015, FR-016, FR-024,
FR-027, FR-032).

- Crear deja un Borrador con la persona como autora. Un código repetido es `code-taken`; un
  contenido igual al de otro ítem (huella normalizada) es `duplicate-item`.
- Guardar el borrador compara la revisión (`If-Match`): sobre lo publicado o lo retirado crea una
  versión nueva; sobre una versión En revisión vuelve a Borrador salvo `keep_in_review`, que exige
  contenido sin problemas.
- Enviar a revisión exige contenido sin problemas (`validation-error` con la lista).
"""

from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from saber_uli.content.application.resolution import context_text, item_hashes
from saber_uli.content.application.review import load_for_change
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.application.validation import module_rules, version_issues
from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.errors import CodeTakenError, DuplicateItemError
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import ItemContent, ItemKind
from saber_uli.content.domain.validation import ContentIssue
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import RuleViolationError


class UnknownModuleError(RuleViolationError):
    slug = "validation-error"


class Authoring:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def create(
        self, *, code: str, module: str, kind: ItemKind, content: ItemContent, actor: UUID
    ) -> Item:
        async with self._uow_factory() as uow:
            if await uow.modules.get(module) is None:
                raise UnknownModuleError("El módulo indicado no existe.")
            if await uow.items.get_by_code(code) is not None:
                raise CodeTakenError("Ya existe un ítem con ese código.")
            context_version_id, hash_, print_ = await _hashes(uow, content, excluding=None)
            item = Item.create(
                code=code,
                module_code=module,
                kind=kind,
                origin=Origin.TEACHER,
                content=content,
                content_hash=hash_,
                fingerprint=print_,
                context_version_id=context_version_id,
                actor=actor,
                now=self._clock.now(),
            )
            await uow.items.add(item)
            await uow.commit()
        return item

    async def save_draft(
        self,
        code: str,
        content: ItemContent,
        actor: UUID,
        *,
        expected_revision: int,
        keep_in_review: bool = False,
    ) -> Item:
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, expected_revision)
            context_version_id, hash_, print_ = await _hashes(uow, content, excluding=item.id)
            issues: list[ContentIssue] = []
            if keep_in_review:
                issues = await _issues_for(uow, item, content, context_version_id)
            item.edit(
                content,
                hash_,
                print_,
                context_version_id,
                actor,
                self._clock.now(),
                keep_in_review=keep_in_review,
                issues=issues,
            )
            await uow.items.save(item)
            await uow.commit()
        return item

    async def submit(self, code: str, actor: UUID, *, expected_revision: int) -> Item:
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, expected_revision)
            issues: list[ContentIssue] = []
            version = item.open
            if version is not None:
                rules = await module_rules(uow, item.module_code)
                if rules is not None:
                    issues = await version_issues(uow, rules, item, version)
            item.submit(actor, self._clock.now(), issues=issues)
            await uow.items.save(item)
            await uow.commit()
        return item


async def _hashes(
    uow: ContentUnitOfWork, content: ItemContent, *, excluding: UUID | None
) -> tuple[UUID | None, bytes, bytes]:
    """Versión vigente del contexto, huellas y comprobación de duplicados (FR-032)."""
    context_version_id = None
    text = None
    if content.context_code is not None:
        context = await uow.contexts.get_by_code(content.context_code)
        if context is not None:
            context_version_id = context.current.id
            text = context_text(context.current.content)
    hash_, print_ = item_hashes(content, text)
    duplicate = await uow.items.code_with_fingerprint(print_, excluding=excluding)
    if duplicate is not None:
        raise DuplicateItemError(f"El contenido coincide con el ítem {duplicate}.")
    return context_version_id, hash_, print_


async def _issues_for(
    uow: ContentUnitOfWork, item: Item, content: ItemContent, context_version_id: UUID | None
) -> list[ContentIssue]:
    version = item.open or item.published
    if version is None:
        return []
    rules = await module_rules(uow, item.module_code)
    if rules is None:
        return []
    probe = replace(version, content=content, context_version_id=context_version_id)
    return await version_issues(uow, rules, item, probe)
