"""Rúbricas de Comunicación escrita (FR-004; data-model §2.3).

Una rúbrica tiene una condición de pertinencia y al menos una dimensión (planteamiento,
organización, forma de expresión…), cada una con al menos dos niveles.
"""

from dataclasses import dataclass
from uuid import UUID

from saber_uli.shared.domain.errors import RuleViolationError


class InvalidRubricError(RuleViolationError):
    slug = "invalid-rubric"


@dataclass(frozen=True)
class RelevanceCondition:
    name: str
    description: str


@dataclass(frozen=True)
class RubricLevel:
    level: int
    description: str


@dataclass(frozen=True)
class RubricDimension:
    code: str
    name: str
    levels: tuple[RubricLevel, ...]


@dataclass(frozen=True)
class Rubric:
    id: UUID | None
    code: str
    name: str
    relevance_condition: RelevanceCondition
    dimensions: tuple[RubricDimension, ...]
    note: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.dimensions:
            raise InvalidRubricError("La rúbrica necesita al menos una dimensión.")
        for dimension in self.dimensions:
            if len(dimension.levels) < 2:
                raise InvalidRubricError(
                    f"La dimensión {dimension.code} necesita al menos dos niveles."
                )
