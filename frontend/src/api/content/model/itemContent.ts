/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { Difficulty } from "./difficulty";
import type { Option } from "./option";
import type { TaxonomyTags } from "./taxonomyTags";

/**
 * Contenido de una versión. En un Borrador se aceptan campos incompletos (salvo los
 * requeridos aquí); la validez completa se exige al enviar a revisión (FR-024).
 */
export interface ItemContent {
  difficulty: Difficulty;
  context_code?: BusinessCode | null;
  taxonomy: TaxonomyTags;
  /**
   * Enunciado; en CE, la pregunta
   * @maxLength 5000
   */
  stem_md: string;
  /**
   * @maxItems 4
   * @nullable
   */
  options?: Option[] | null;
  /**
   * Solo `matching`
   * @nullable
   * @pattern ^[A-H]$
   */
  answer_key?: string | null;
  /** @maxLength 5000 */
  explanation_md: string;
  /**
   * Solo CE
   * @maxLength 5000
   * @nullable
   */
  prompt_context_md?: string | null;
  /**
   * Solo CE
   * @nullable
   */
  rubric_id?: string | null;
}
