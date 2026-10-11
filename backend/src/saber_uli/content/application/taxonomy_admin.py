"""Mantenimiento de la taxonomía y de la meta de cada módulo (US9; FR-001, FR-040, FR-045).

Las categorías son datos: el administrador las crea, edita, desactiva y borra. Una categoría en
uso (por una versión de ítem, de contexto o por una hija) no se borra: se desactiva, y deja de
ofrecerse para lo nuevo sin tocar lo que ya la usa. Cuando los pesos de un tipo en un módulo no
suman cerca de 1 se avisa, sin impedir el cambio (se puede estar a mitad de un ajuste). Cada
cambio queda en `content.taxonomy_changes` con el antes y el después.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from saber_uli.content.application.ports import TaxonomyChange
from saber_uli.content.application.queries.modules import ModuleView, NodeView
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.errors import (
    InvalidTaxonomyNodeError,
    ModuleNotFoundError,
    TaxonomyCodeTakenError,
    TaxonomyNodeInUseError,
    TaxonomyNodeNotFoundError,
)
from saber_uli.content.domain.taxonomy import (
    PARENT_KIND,
    PartFormat,
    TaxonomyNode,
    TaxonomyNodeKind,
)
from saber_uli.shared.domain.clock import Clock

K = TaxonomyNodeKind
WEIGHT_RANGE = (Decimal("0.95"), Decimal("1.05"))
_PLURAL = {
    K.COMPETENCE: "las competencias",
    K.ASSERTION: "las afirmaciones",
    K.EVIDENCE: "las evidencias",
    K.COMPONENT: "los componentes",
    K.SITUATION: "las situaciones",
    K.TEXT_TYPE: "los tipos de texto",
    K.PART: "las partes",
}
_PARENT_NAME = {K.COMPETENCE: "una competencia", K.ASSERTION: "una afirmación"}
_UNSET: Any = object()


@dataclass(frozen=True)
class NewNode:
    module: str
    kind: TaxonomyNodeKind
    code: str
    name: str
    description: str | None = None
    parent_id: UUID | None = None
    target_weight: Decimal | None = None
    part_options: int | None = None
    part_format: PartFormat | None = None


@dataclass(frozen=True)
class NodeResult:
    view: NodeView
    warnings: list[str]


def _snapshot(node: TaxonomyNode) -> dict[str, Any]:
    return {
        "module": node.module_code,
        "kind": node.kind.value,
        "code": node.code,
        "name": node.name,
        "description": node.description,
        "parent_id": None if node.parent_id is None else str(node.parent_id),
        "target_weight": None if node.target_weight is None else str(node.target_weight),
        "part_options": node.part_options,
        "part_format": None if node.part_format is None else node.part_format.value,
        "active": node.active,
    }


class TaxonomyAdmin:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def update_module(self, code: str, *, bank_target: int, actor: UUID) -> ModuleView:
        async with self._uow_factory() as uow:
            module = await uow.modules.get(code)
            if module is None:
                raise ModuleNotFoundError("El módulo no existe.")
            updated = replace(module, bank_target=bank_target)
            await uow.modules.save(updated)
            await self._record(
                uow,
                "module",
                code,
                "updated",
                {"bank_target": module.bank_target},
                {"bank_target": bank_target},
                actor,
            )
            nodes = await uow.taxonomy.list(module_code=code)
            used = await uow.taxonomy.used_ids()
            await uow.commit()
        return ModuleView(
            module=updated,
            nodes=[NodeView(node=n, in_use=n.id in used) for n in nodes if n.active],
        )

    async def create_node(self, new: NewNode, actor: UUID) -> NodeResult:
        async with self._uow_factory() as uow:
            if await uow.modules.get(new.module) is None:
                raise InvalidTaxonomyNodeError("El módulo no existe.")
            if await uow.taxonomy.get_by_code(new.code) is not None:
                raise TaxonomyCodeTakenError(f"Ya existe una categoría con el código {new.code}.")
            await self._check_parent(uow, new)
            siblings = [
                n for n in await uow.taxonomy.list(module_code=new.module) if n.kind is new.kind
            ]
            node = TaxonomyNode(
                id=uuid4(),
                module_code=new.module,
                kind=new.kind,
                code=new.code,
                name=new.name.strip(),
                position=max((n.position for n in siblings), default=0) + 1,
                description=new.description,
                parent_id=new.parent_id,
                target_weight=new.target_weight,
                part_options=new.part_options if new.kind is K.PART else None,
                part_format=new.part_format if new.kind is K.PART else None,
            )
            await uow.taxonomy.add(node)
            await self._record(uow, "node", str(node.id), "created", None, _snapshot(node), actor)
            warnings = await _weight_warnings(uow, node)
            await uow.commit()
        return NodeResult(NodeView(node=node, in_use=False), warnings)

    async def update_node(
        self,
        node_id: UUID,
        actor: UUID,
        *,
        name: str = _UNSET,
        description: str | None = _UNSET,
        target_weight: Decimal | None = _UNSET,
        active: bool = _UNSET,
    ) -> NodeResult:
        async with self._uow_factory() as uow:
            node = await uow.taxonomy.get(node_id)
            if node is None:
                raise TaxonomyNodeNotFoundError("La categoría no existe.")
            before = _snapshot(node)
            was_active = node.active
            if name is not _UNSET:
                node.name = name.strip()
            if description is not _UNSET:
                node.description = description
            if target_weight is not _UNSET:
                node.target_weight = target_weight
            if active is not _UNSET:
                node.active = active
            await uow.taxonomy.save(node)
            action = (
                "deactivated"
                if was_active and not node.active
                else "reactivated"
                if not was_active and node.active
                else "updated"
            )
            await self._record(uow, "node", str(node_id), action, before, _snapshot(node), actor)
            warnings = await _weight_warnings(uow, node)
            in_use = node_id in await uow.taxonomy.used_ids()
            await uow.commit()
        return NodeResult(NodeView(node=node, in_use=in_use), warnings)

    async def delete_node(self, node_id: UUID, actor: UUID) -> None:
        async with self._uow_factory() as uow:
            node = await uow.taxonomy.get(node_id)
            if node is None:
                raise TaxonomyNodeNotFoundError("La categoría no existe.")
            if node_id in await uow.taxonomy.used_ids():
                raise TaxonomyNodeInUseError(
                    "La categoría está en uso (por ítems, contextos o categorías hijas): "
                    "desactívala en lugar de borrarla."
                )
            await uow.taxonomy.delete(node_id)
            await self._record(uow, "node", str(node_id), "deleted", _snapshot(node), None, actor)
            await uow.commit()

    async def _check_parent(self, uow: ContentUnitOfWork, new: NewNode) -> None:
        expected = PARENT_KIND.get(new.kind)
        if expected is None:
            if new.parent_id is not None:
                raise InvalidTaxonomyNodeError("Este tipo de categoría no tiene categoría padre.")
            return
        parent = None if new.parent_id is None else await uow.taxonomy.get(new.parent_id)
        if parent is None or parent.kind is not expected or parent.module_code != new.module:
            raise InvalidTaxonomyNodeError(
                f"La categoría padre debe ser {_PARENT_NAME[expected]} del mismo módulo."
            )

    async def _record(
        self,
        uow: ContentUnitOfWork,
        target: str,
        target_id: str,
        action: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        actor: UUID,
    ) -> None:
        await uow.taxonomy_changes.add(
            TaxonomyChange(
                changed_by=actor,
                changed_at=self._clock.now(),
                target=target,
                target_id=target_id,
                action=action,
                before=before,
                after=after,
            )
        )


async def _weight_warnings(uow: ContentUnitOfWork, node: TaxonomyNode) -> list[str]:
    """Aviso si los pesos activos de ese tipo en el módulo no suman cerca de 1."""
    weights = [
        n.target_weight
        for n in await uow.taxonomy.list(module_code=node.module_code)
        if n.kind is node.kind and n.active and n.target_weight is not None
    ]
    if not weights:
        return []
    total = sum(weights, Decimal(0))
    low, high = WEIGHT_RANGE
    if low <= total <= high:
        return []
    shown = format(total.normalize(), "f").replace(".", ",")
    return [
        f"Los pesos de {_PLURAL[node.kind]} de {node.module_code} suman {shown}; "
        "deberían sumar cerca de 1."
    ]
