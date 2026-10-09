"""Contenido de una versión de ítem y su validación (FR-002 a FR-006, FR-024, FR-031).

Tres tipos de ítem: selección (única respuesta), emparejamiento (Inglés parte 1, contra las
opciones compartidas del contexto) y consigna de escritura (con rúbrica). `validate_item` devuelve
los problemas sin lanzar: un Borrador se guarda con ellos (`content_issues`) y enviar a revisión
exige cero.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from saber_uli.content.domain.context import ContextContent, ContextKind
from saber_uli.content.domain.module import ModuleRules, QuestionType
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyTags
from saber_uli.content.domain.validation import ContentIssue, ValidationRule

R = ValidationRule
MAX_MATCHING_ITEMS_PER_CONTEXT = 5


class ItemKind(StrEnum):
    SELECTION = "selection"
    MATCHING = "matching"
    WRITING_PROMPT = "writing_prompt"


class VersionState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    RETIRED = "retired"

    @property
    def is_open(self) -> bool:
        return self in (VersionState.DRAFT, VersionState.IN_REVIEW)


class Difficulty(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Option:
    key: str
    text: str
    correct: bool
    feedback: str


@dataclass(frozen=True)
class ItemContent:
    difficulty: Difficulty
    stem_md: str
    explanation_md: str
    taxonomy: TaxonomyTags = field(default_factory=TaxonomyTags)
    options: tuple[Option, ...] | None = None
    answer_key: str | None = None
    prompt_context_md: str | None = None
    rubric_id: UUID | None = None
    context_code: str | None = None


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


def validate_item(
    kind: ItemKind,
    content: ItemContent,
    rules: ModuleRules,
    *,
    context: ContextContent | None,
    matching_siblings: int = 0,
    already_used: frozenset[UUID] = frozenset(),
) -> list[ContentIssue]:
    """Problemas del contenido. `context` es la versión vigente del contexto referenciado (None si
    no existe); `matching_siblings`, cuántos otros ítems de emparejamiento usan ese contexto."""
    issues: list[ContentIssue] = []
    writing_module = rules.module.question_type is QuestionType.WRITING
    if writing_module != (kind is ItemKind.WRITING_PROMPT):
        issues.append(
            ContentIssue(
                "kind", R.TAXONOMY_MISMATCH, f"El tipo no corresponde a {rules.module.name}."
            )
        )
    if _blank(content.stem_md):
        issues.append(ContentIssue("stem_md", R.REQUIRED, "Escribe el enunciado."))
    if _blank(content.explanation_md):
        issues.append(
            ContentIssue(
                "explanation_md", R.EXPLANATION_REQUIRED, "Escribe la explicación general."
            )
        )
    if content.context_code is not None and context is None:
        issues.append(
            ContentIssue("context_code", R.CONTEXT_UNKNOWN, "El contexto indicado no existe.")
        )
    issues.extend(rules.check_tags(content.taxonomy, already_used=already_used))
    part_format = rules.part_format(content.taxonomy.part_id)
    if kind is ItemKind.SELECTION:
        if part_format is PartFormat.MATCHING:
            issues.append(
                ContentIssue(
                    "taxonomy.part_id",
                    R.TAXONOMY_MISMATCH,
                    "Esta parte es de emparejamiento: el ítem debe usar las opciones del contexto.",
                )
            )
        issues.extend(_check_options(content, rules))
    elif kind is ItemKind.MATCHING:
        issues.extend(_check_matching(content, part_format, context, matching_siblings))
    else:
        issues.extend(_check_writing(content, rules))
    return issues


def _check_options(content: ItemContent, rules: ModuleRules) -> list[ContentIssue]:
    options = list(content.options or ())
    expected = rules.option_count(content.taxonomy.part_id)
    keys = [option.key for option in options]
    issues: list[ContentIssue] = []
    if (expected is not None and len(options) != expected) or keys != [
        chr(ord("A") + index) for index in range(len(keys))
    ]:
        issues.append(
            ContentIssue(
                "options",
                R.OPTION_COUNT,
                f"El ítem debe tener {expected} opciones con claves desde la A, en orden.",
            )
        )
    if sum(option.correct for option in options) != 1:
        issues.append(
            ContentIssue(
                "options", R.SINGLE_CORRECT_OPTION, "Marca exactamente una opción correcta."
            )
        )
    for option in options:
        if _blank(option.text):
            issues.append(
                ContentIssue(f"options[{option.key}].text", R.REQUIRED, "Escribe la opción.")
            )
        if _blank(option.feedback):
            issues.append(
                ContentIssue(
                    f"options[{option.key}].feedback",
                    R.OPTION_FEEDBACK_REQUIRED,
                    f"La opción {option.key} necesita su retroalimentación.",
                )
            )
    return issues


def _check_matching(
    content: ItemContent,
    part_format: PartFormat | None,
    context: ContextContent | None,
    matching_siblings: int,
) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    if content.options:
        issues.append(
            ContentIssue(
                "options", R.OPTION_COUNT, "El emparejamiento usa las opciones del contexto."
            )
        )
    if content.taxonomy.part_id is not None and part_format is not PartFormat.MATCHING:
        issues.append(
            ContentIssue(
                "taxonomy.part_id", R.TAXONOMY_MISMATCH, "La parte no es de emparejamiento."
            )
        )
    if content.context_code is None:
        issues.append(
            ContentIssue("context_code", R.REQUIRED, "Elige el contexto con las opciones.")
        )
    elif context is not None and context.kind is not ContextKind.SHARED_OPTIONS:
        issues.append(
            ContentIssue(
                "context_code", R.TAXONOMY_MISMATCH, "El contexto no tiene opciones compartidas."
            )
        )
    if matching_siblings >= MAX_MATCHING_ITEMS_PER_CONTEXT:
        issues.append(
            ContentIssue(
                "context_code",
                R.OPTION_COUNT,
                f"Un contexto admite como máximo {MAX_MATCHING_ITEMS_PER_CONTEXT} descripciones.",
            )
        )
    if _blank(content.answer_key):
        issues.append(ContentIssue("answer_key", R.REQUIRED, "Elige la respuesta correcta."))
    elif context is not None and content.answer_key not in context.shared_keys():
        issues.append(
            ContentIssue(
                "answer_key",
                R.MATCHING_KEY_UNKNOWN,
                "La respuesta no está entre las opciones del contexto.",
            )
        )
    return issues


def _check_writing(content: ItemContent, rules: ModuleRules) -> list[ContentIssue]:
    issues: list[ContentIssue] = []
    if content.options:
        issues.append(ContentIssue("options", R.OPTION_COUNT, "Una consigna no lleva opciones."))
    if _blank(content.prompt_context_md):
        issues.append(
            ContentIssue("prompt_context_md", R.REQUIRED, "Escribe el contexto de la consigna.")
        )
    if content.rubric_id is None:
        issues.append(ContentIssue("rubric_id", R.REQUIRED, "Elige la rúbrica."))
    elif not rules.has_rubric(content.rubric_id):
        issues.append(ContentIssue("rubric_id", R.RUBRIC_UNKNOWN, "La rúbrica no existe."))
    return issues
