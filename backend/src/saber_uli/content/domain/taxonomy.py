"""Taxonomía del ICFES como datos (FR-001; data-model §2.2).

Competencias, afirmaciones y evidencias forman un árbol (evidencia → afirmación → competencia).
Componentes, tipos de situación, tipos de texto y partes de Inglés son categorías planas. Una
categoría inactiva no se ofrece en ítems nuevos, pero los que ya la usan siguen válidos (FR-045).
"""

from dataclasses import dataclass, fields
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class TaxonomyNodeKind(StrEnum):
    COMPETENCE = "competence"
    ASSERTION = "assertion"
    EVIDENCE = "evidence"
    COMPONENT = "component"
    SITUATION = "situation"
    TEXT_TYPE = "text_type"
    PART = "part"


class PartFormat(StrEnum):
    MATCHING = "matching"
    SELECTION = "selection"


# El tipo del padre de cada categoría del árbol.
PARENT_KIND: dict[TaxonomyNodeKind, TaxonomyNodeKind] = {
    TaxonomyNodeKind.ASSERTION: TaxonomyNodeKind.COMPETENCE,
    TaxonomyNodeKind.EVIDENCE: TaxonomyNodeKind.ASSERTION,
}

# Tipos que etiquetan ítems (el tipo de texto etiqueta contextos).
ITEM_TAG_KINDS: tuple[TaxonomyNodeKind, ...] = (
    TaxonomyNodeKind.COMPETENCE,
    TaxonomyNodeKind.ASSERTION,
    TaxonomyNodeKind.EVIDENCE,
    TaxonomyNodeKind.COMPONENT,
    TaxonomyNodeKind.SITUATION,
    TaxonomyNodeKind.PART,
)


@dataclass
class TaxonomyNode:
    id: UUID
    module_code: str
    kind: TaxonomyNodeKind
    code: str
    name: str
    position: int
    description: str | None = None
    parent_id: UUID | None = None
    target_weight: Decimal | None = None
    part_options: int | None = None
    part_format: PartFormat | None = None
    active: bool = True


@dataclass(frozen=True)
class TaxonomyTags:
    """Categorías de una versión de ítem; cuáles son obligatorias depende del módulo."""

    competence_id: UUID | None = None
    assertion_id: UUID | None = None
    evidence_id: UUID | None = None
    component_id: UUID | None = None
    situation_id: UUID | None = None
    part_id: UUID | None = None

    def get(self, kind: TaxonomyNodeKind) -> UUID | None:
        value: UUID | None = getattr(self, field_for(kind))
        return value

    def ids(self) -> frozenset[UUID]:
        return frozenset(
            value for value in (getattr(self, f.name) for f in fields(self)) if value is not None
        )


def field_for(kind: TaxonomyNodeKind) -> str:
    """Nombre del campo de `TaxonomyTags` para un tipo de categoría (`competence_id`…)."""
    if kind not in ITEM_TAG_KINDS:
        raise ValueError(f"el tipo {kind.value!r} no etiqueta ítems")
    return f"{kind.value}_id"
