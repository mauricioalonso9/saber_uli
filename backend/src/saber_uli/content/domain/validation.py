"""Problemas de contenido (FR-024, FR-031; contrato: `ValidationRule`).

Un problema dice qué campo incumple qué regla. Un Borrador puede guardarse con problemas
(`content_issues`); enviar a revisión exige cero. La importación usa el mismo catálogo para el
reporte por ítem.
"""

from dataclasses import dataclass
from enum import StrEnum


class ValidationRule(StrEnum):
    REQUIRED = "required"
    SINGLE_CORRECT_OPTION = "single_correct_option"
    OPTION_COUNT = "option_count"
    OPTION_FEEDBACK_REQUIRED = "option_feedback_required"
    EXPLANATION_REQUIRED = "explanation_required"
    TAXONOMY_UNKNOWN = "taxonomy_unknown"
    TAXONOMY_INACTIVE = "taxonomy_inactive"
    TAXONOMY_MISMATCH = "taxonomy_mismatch"
    CONTEXT_UNKNOWN = "context_unknown"
    CONTEXT_WORD_LIMIT = "context_word_limit"
    ALT_TEXT_REQUIRED = "alt_text_required"
    MATCHING_KEY_UNKNOWN = "matching_key_unknown"
    DUPLICATE_ITEM = "duplicate_item"
    DUPLICATE_IN_FILE = "duplicate_in_file"
    UNSUPPORTED_IN_TEMPLATE = "unsupported_in_template"
    CONTEXT_TEXT_MISMATCH = "context_text_mismatch"
    RUBRIC_UNKNOWN = "rubric_unknown"
    CHANGED_SINCE_PREVIEW = "changed_since_preview"


@dataclass(frozen=True)
class ContentIssue:
    field: str
    rule: ValidationRule
    message: str
