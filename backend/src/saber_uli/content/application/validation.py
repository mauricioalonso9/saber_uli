"""Problemas de contenido de una versión guardada (FR-024; contrato: `content_issues`).

Arma las reglas del módulo desde la base y valida la versión con su contexto y con los otros
ítems de emparejamiento del mismo contexto. Las categorías que la versión ya usa siguen válidas
aunque se hayan desactivado (FR-045).
"""

from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import ItemKind, ItemVersion, validate_item
from saber_uli.content.domain.module import ModuleRules
from saber_uli.content.domain.validation import ContentIssue


async def module_rules(uow: ContentUnitOfWork, module_code: str) -> ModuleRules | None:
    module = await uow.modules.get(module_code)
    if module is None:
        return None
    nodes = await uow.taxonomy.list(module_code=module_code)
    rubrics = await uow.rubrics.list()
    active = frozenset(r.id for r in rubrics if r.active and r.id is not None)
    return ModuleRules(module, nodes, rubric_ids=active)


async def version_issues(
    uow: ContentUnitOfWork, rules: ModuleRules, item: Item, version: ItemVersion
) -> list[ContentIssue]:
    context = None
    siblings = 0
    if version.context_version_id is not None:
        stored = await uow.contexts.get_version(version.context_version_id)
        context = None if stored is None else stored.content
        if item.kind is ItemKind.MATCHING:
            siblings = await uow.items.count_matching_in_context(
                version.context_version_id, excluding=item.id
            )
    return validate_item(
        item.kind,
        version.content,
        rules,
        context=context,
        matching_siblings=siblings,
        already_used=version.content.taxonomy.ids(),
    )
