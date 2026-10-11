/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { RubricInputDimensionsItem } from "./rubricInputDimensionsItem";
import type { RubricInputRelevanceCondition } from "./rubricInputRelevanceCondition";

export interface RubricInput {
  /** @pattern ^RUB-[A-Z0-9-]{1,20}$ */
  code: string;
  /**
   * @minLength 1
   * @maxLength 200
   */
  name: string;
  /**
   * @maxLength 1000
   * @nullable
   */
  note?: string | null;
  active: boolean;
  relevance_condition: RubricInputRelevanceCondition;
  /** @minItems 1 */
  dimensions: RubricInputDimensionsItem[];
}
