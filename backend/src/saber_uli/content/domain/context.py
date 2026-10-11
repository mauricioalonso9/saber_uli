"""Contextos compartidos y sus versiones (FR-005, FR-007, FR-009, FR-020; data-model §2.5).

Un contexto es el material que comparten uno o varios ítems: texto, tabla, imagen o lista de
opciones compartidas (la parte 1 de Inglés). Cada edición crea una versión nueva; las versiones de
ítem fijan la versión de su contexto (research R-02).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from saber_uli.content.domain.module import ModuleRules
from saber_uli.content.domain.taxonomy import TaxonomyNodeKind
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.content.domain.word_count import count_words

R = ValidationRule


class ContextKind(StrEnum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    SHARED_OPTIONS = "shared_options"


class Origin(StrEnum):
    SEED = "seed"
    TEACHER = "teacher"
    AI = "ai"


@dataclass(frozen=True)
class SharedOption:
    key: str
    text: str
    feedback: str


@dataclass(frozen=True)
class ContextContent:
    kind: ContextKind
    title: str
    body_md: str | None = None
    media_id: UUID | None = None
    alt_text: str | None = None
    text_type_node_id: UUID | None = None
    part_node_id: UUID | None = None
    subtype: str | None = None
    shared_options: tuple[SharedOption, ...] | None = None

    def shared_keys(self) -> frozenset[str]:
        return frozenset(option.key for option in self.shared_options or ())


@dataclass
class ContextVersion:
    id: UUID | None
    number: int
    content: ContextContent
    word_count: int | None
    origin: Origin
    content_hash: bytes
    created_by: UUID | None
    created_at: datetime


@dataclass
class Context:
    """Agregado: código estable, versión vigente y revisión para `If-Match` (R-09)."""

    id: UUID | None
    code: str
    module_code: str
    current: ContextVersion
    revision: int = 0
    seed_hash: bytes | None = None


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _keys_in_order(keys: list[str]) -> bool:
    return keys == [chr(ord("A") + index) for index in range(len(keys))]


def word_count_for(content: ContextContent, rules: ModuleRules) -> int | None:
    """Palabras del texto, solo en módulos con máximo (Lectura crítica, FR-007)."""
    if rules.module.max_context_words is None or content.body_md is None:
        return None
    return count_words(content.body_md)


def _check_node(
    rules: ModuleRules, node_id: UUID | None, kind: TaxonomyNodeKind, field: str
) -> list[ContentIssue]:
    if node_id is None:
        if any(node.kind is kind for node in rules.nodes()):
            return [ContentIssue(field, R.REQUIRED, "Falta la categoría del contexto.")]
        return []
    node = rules.node(node_id)
    if node is None:
        return [ContentIssue(field, R.TAXONOMY_UNKNOWN, "La categoría no existe en el módulo.")]
    if node.kind is not kind:
        return [ContentIssue(field, R.TAXONOMY_MISMATCH, f"El código {node.code} no corresponde.")]
    return []


def validate_context(content: ContextContent, rules: ModuleRules) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    if _blank(content.title):
        issues.append(ContentIssue("title", R.REQUIRED, "Escribe el título del contexto."))
    if content.kind in (ContextKind.TEXT, ContextKind.TABLE) and _blank(content.body_md):
        issues.append(ContentIssue("body_md", R.REQUIRED, "Escribe el texto del contexto."))
    if content.kind is ContextKind.IMAGE:
        if content.media_id is None:
            issues.append(ContentIssue("media_id", R.REQUIRED, "Sube la imagen del contexto."))
        if _blank(content.alt_text):
            issues.append(
                ContentIssue(
                    "alt_text",
                    R.ALT_TEXT_REQUIRED,
                    "Describe la imagen para quienes usan lector de pantalla.",
                )
            )
    if content.kind is ContextKind.SHARED_OPTIONS:
        issues.extend(_check_shared_options(content, rules))
    words = word_count_for(content, rules)
    limit = rules.module.max_context_words
    if words is not None and limit is not None and words > limit:
        issues.append(
            ContentIssue(
                "body_md",
                R.CONTEXT_WORD_LIMIT,
                f"El texto tiene {words}/{limit} palabras; el máximo es {limit}.",
            )
        )
    issues.extend(
        _check_node(
            rules, content.text_type_node_id, TaxonomyNodeKind.TEXT_TYPE, "text_type_node_id"
        )
    )
    issues.extend(_check_node(rules, content.part_node_id, TaxonomyNodeKind.PART, "part_node_id"))
    return issues


def _check_shared_options(content: ContextContent, rules: ModuleRules) -> list[ContentIssue]:
    options = list(content.shared_options or ())
    issues: list[ContentIssue] = []
    expected = rules.option_count(content.part_node_id)
    if (expected is not None and len(options) != expected) or not _keys_in_order(
        [option.key for option in options]
    ):
        issues.append(
            ContentIssue(
                "shared_options",
                R.OPTION_COUNT,
                f"La lista debe tener {expected} opciones con claves desde la A, en orden.",
            )
        )
    for option in options:
        if _blank(option.text):
            issues.append(
                ContentIssue(f"shared_options[{option.key}].text", R.REQUIRED, "Escribe la opción.")
            )
        if _blank(option.feedback):
            issues.append(
                ContentIssue(
                    f"shared_options[{option.key}].feedback",
                    R.OPTION_FEEDBACK_REQUIRED,
                    f"La opción {option.key} necesita su retroalimentación.",
                )
            )
    return issues
