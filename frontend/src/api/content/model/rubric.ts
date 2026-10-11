/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { RubricDimensionsItem } from "./rubricDimensionsItem";
import type { RubricRelevanceCondition } from "./rubricRelevanceCondition";

export interface Rubric {
  id: string;
  code: string;
  name: string;
  /** @nullable */
  note?: string | null;
  active: boolean;
  relevance_condition: RubricRelevanceCondition;
  dimensions: RubricDimensionsItem[];
}
