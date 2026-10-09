/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ContentModuleQuestionType } from "./contentModuleQuestionType";
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { TaxonomyNode } from "./taxonomyNode";

export interface ContentModule {
  code: ModuleCodeValue;
  name: string;
  question_type: ContentModuleQuestionType;
  /** @nullable */
  options_per_item?: number | null;
  /** @nullable */
  max_context_words?: number | null;
  exam_questions: number;
  bank_target: number;
  /** Categorías en orden; el árbol se arma con `parent_id` */
  nodes: TaxonomyNode[];
}
