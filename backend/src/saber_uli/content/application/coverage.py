"""Cobertura del banco frente a la distribución del examen (US7; FR-039, FR-040; research R-16).

Agrupa por el tipo de categoría que tiene pesos objetivo: el de más categorías activas con peso
(LC por afirmación, RC y CC por competencia, Inglés por parte). Los pesos y la meta del módulo son
datos que edita el administrador (FR-040), no constantes del código. Cuentan los ítems Publicados
y En revisión; los Borradores y los retirados no.
"""

import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.errors import ModuleNotFoundError
from saber_uli.content.domain.taxonomy import ITEM_TAG_KINDS, TaxonomyNodeKind, field_for

# Un módulo sin pesos (Comunicación escrita) informa solo los totales; el contrato pide igual un
# tipo de agrupación.
_WITHOUT_WEIGHTS = TaxonomyNodeKind.COMPETENCE


@dataclass(frozen=True)
class CategoryCoverage:
    node_id: UUID
    code: str
    name: str
    target_weight: float | None
    published: int
    in_review: int
    published_share: float
    missing: int
    below_target: bool


@dataclass(frozen=True)
class ModuleCoverage:
    module: str
    grouped_by: str
    bank_target: int
    published_total: int
    in_review_total: int
    categories: list[CategoryCoverage]


class Coverage:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def module(self, code: str) -> ModuleCoverage:
        async with self._uow_factory() as uow:
            module = await uow.modules.get(code)
            if module is None:
                raise ModuleNotFoundError("El módulo no existe.")
            nodes = [n for n in await uow.taxonomy.list(module_code=code) if n.active]
            weighted = Counter(
                n.kind for n in nodes if n.kind in ITEM_TAG_KINDS and n.target_weight is not None
            )
            kind = max(ITEM_TAG_KINDS, key=lambda k: weighted[k]) if weighted else _WITHOUT_WEIGHTS
            counts = await uow.items.coverage_counts(code, field_for(kind))
        categories = []
        if weighted:
            for node in sorted(
                (n for n in nodes if n.kind is kind), key=lambda n: (n.position, n.code)
            ):
                published, in_review = counts.by_node.get(node.id, (0, 0))
                target = (
                    None
                    if node.target_weight is None
                    else math.ceil(module.bank_target * node.target_weight)
                )
                missing = 0 if target is None else max(0, target - published)
                categories.append(
                    CategoryCoverage(
                        node_id=node.id,
                        code=node.code,
                        name=node.name,
                        target_weight=None
                        if node.target_weight is None
                        else float(node.target_weight),
                        published=published,
                        in_review=in_review,
                        published_share=published / counts.published_total
                        if counts.published_total
                        else 0.0,
                        missing=missing,
                        below_target=missing > 0,
                    )
                )
        return ModuleCoverage(
            module=module.code,
            grouped_by=kind.value,
            bank_target=module.bank_target,
            published_total=counts.published_total,
            in_review_total=counts.in_review_total,
            categories=categories,
        )
