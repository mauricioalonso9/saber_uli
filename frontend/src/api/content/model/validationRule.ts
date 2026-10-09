/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

/**
 * Catálogo de reglas de validación del contenido (FR-031)
 */
export type ValidationRule = (typeof ValidationRule)[keyof typeof ValidationRule];

export const ValidationRule = {
  required: "required",
  single_correct_option: "single_correct_option",
  option_count: "option_count",
  option_feedback_required: "option_feedback_required",
  explanation_required: "explanation_required",
  taxonomy_unknown: "taxonomy_unknown",
  taxonomy_inactive: "taxonomy_inactive",
  taxonomy_mismatch: "taxonomy_mismatch",
  context_unknown: "context_unknown",
  context_word_limit: "context_word_limit",
  alt_text_required: "alt_text_required",
  matching_key_unknown: "matching_key_unknown",
  duplicate_item: "duplicate_item",
  duplicate_in_file: "duplicate_in_file",
  unsupported_in_template: "unsupported_in_template",
  context_text_mismatch: "context_text_mismatch",
  rubric_unknown: "rubric_unknown",
  changed_since_preview: "changed_since_preview",
} as const;
