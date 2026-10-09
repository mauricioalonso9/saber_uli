"""Módulos con su taxonomía (contrato: `listContentModules`; FR-001, FR-045).

Cada categoría dice si está en uso (la usa una versión de ítem, una versión de contexto o una
categoría hija): en uso no se puede borrar, solo desactivar.
"""

from collections.abc import Callable
from dataclasses import dataclass

from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.module import Module
from saber_uli.content.domain.taxonomy import TaxonomyNode


@dataclass(frozen=True)
class NodeView:
    node: TaxonomyNode
    in_use: bool


@dataclass(frozen=True)
class ModuleView:
    module: Module
    nodes: list[NodeView]


class ListContentModules:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, *, include_inactive: bool = False) -> list[ModuleView]:
        async with self._uow_factory() as uow:
            modules = await uow.modules.list()
            nodes = await uow.taxonomy.list()
            used = await uow.taxonomy.used_ids()
        by_module: dict[str, list[NodeView]] = {}
        for node in nodes:
            if node.active or include_inactive:
                by_module.setdefault(node.module_code, []).append(
                    NodeView(node=node, in_use=node.id in used)
                )
        return [ModuleView(module=m, nodes=by_module.get(m.code, [])) for m in modules]
