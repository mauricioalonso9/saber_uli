"""Módulos y sus reglas (FR-001 a FR-004; data-model §2.1).

`ModuleRules` reúne un módulo con su taxonomía y responde lo que cada validación necesita: qué
etiquetas son obligatorias, cuántas opciones lleva un ítem, si una parte es de emparejamiento y
si las etiquetas de un ítem son coherentes. Todo sale de los datos, no del código del módulo.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from saber_uli.content.domain.taxonomy import (
    ITEM_TAG_KINDS,
    PARENT_KIND,
    PartFormat,
    TaxonomyNode,
    TaxonomyNodeKind,
    TaxonomyTags,
    field_for,
)
from saber_uli.content.domain.validation import ContentIssue, ValidationRule

_KIND_NAMES = {
    TaxonomyNodeKind.COMPETENCE: "la competencia",
    TaxonomyNodeKind.ASSERTION: "la afirmación",
    TaxonomyNodeKind.EVIDENCE: "la evidencia",
    TaxonomyNodeKind.COMPONENT: "el componente",
    TaxonomyNodeKind.SITUATION: "el tipo de situación",
    TaxonomyNodeKind.PART: "la parte",
}


class QuestionType(StrEnum):
    SELECTION = "selection"
    WRITING = "writing"


@dataclass
class Module:
    code: str
    name: str
    question_type: QuestionType
    options_per_item: int | None
    max_context_words: int | None
    exam_questions: int
    bank_target: int
    position: int


class ModuleRules:
    def __init__(
        self,
        module: Module,
        nodes: Iterable[TaxonomyNode],
        *,
        rubric_ids: frozenset[UUID] = frozenset(),
    ) -> None:
        self.module = module
        self._nodes = {node.id: node for node in nodes if node.module_code == module.code}
        self._rubric_ids = rubric_ids
        present = {node.kind for node in self._nodes.values()}
        self.required_tags = frozenset(kind for kind in ITEM_TAG_KINDS if kind in present)

    def node(self, node_id: UUID | None) -> TaxonomyNode | None:
        return None if node_id is None else self._nodes.get(node_id)

    def nodes(self) -> list[TaxonomyNode]:
        return list(self._nodes.values())

    def has_rubric(self, rubric_id: UUID | None) -> bool:
        return rubric_id is not None and rubric_id in self._rubric_ids

    def option_count(self, part_id: UUID | None) -> int | None:
        """Opciones de un ítem: las del módulo o, en Inglés, las de su parte (FR-002, FR-003)."""
        part = self.node(part_id)
        if part is not None and part.kind is TaxonomyNodeKind.PART:
            return part.part_options
        return self.module.options_per_item

    def part_format(self, part_id: UUID | None) -> PartFormat | None:
        part = self.node(part_id)
        return part.part_format if part is not None and part.kind is TaxonomyNodeKind.PART else None

    def check_tags(
        self, tags: TaxonomyTags, *, already_used: frozenset[UUID] = frozenset()
    ) -> list[ContentIssue]:
        """Etiquetas obligatorias, existentes, del tipo correcto, activas y en el árbol correcto.

        `already_used`: categorías que el ítem ya tenía; siguen válidas aunque estén inactivas.
        """
        issues: list[ContentIssue] = []
        for kind in ITEM_TAG_KINDS:
            field = f"taxonomy.{field_for(kind)}"
            node_id = tags.get(kind)
            if node_id is None:
                if kind in self.required_tags:
                    issues.append(
                        ContentIssue(field, ValidationRule.REQUIRED, f"Falta {_KIND_NAMES[kind]}.")
                    )
                continue
            node = self.node(node_id)
            if node is None:
                issues.append(
                    ContentIssue(
                        field,
                        ValidationRule.TAXONOMY_UNKNOWN,
                        f"{_KIND_NAMES[kind].capitalize()} no existe en {self.module.name}.",
                    )
                )
            elif node.kind is not kind:
                issues.append(
                    ContentIssue(
                        field,
                        ValidationRule.TAXONOMY_MISMATCH,
                        f"El código {node.code} no es {_KIND_NAMES[kind]}.",
                    )
                )
            elif not node.active and node_id not in already_used:
                issues.append(
                    ContentIssue(
                        field,
                        ValidationRule.TAXONOMY_INACTIVE,
                        f"{_KIND_NAMES[kind].capitalize()} {node.code} está desactivada.",
                    )
                )
            elif kind in PARENT_KIND:
                parent_id = tags.get(PARENT_KIND[kind])
                if parent_id is not None and node.parent_id != parent_id:
                    issues.append(
                        ContentIssue(
                            field,
                            ValidationRule.TAXONOMY_MISMATCH,
                            f"{_KIND_NAMES[kind].capitalize()} {node.code} no pertenece a "
                            f"{_KIND_NAMES[PARENT_KIND[kind]]} elegida.",
                        )
                    )
        return issues
