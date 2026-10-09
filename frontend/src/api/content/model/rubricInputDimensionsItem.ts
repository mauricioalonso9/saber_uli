/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { RubricInputDimensionsItemLevelsItem } from "./rubricInputDimensionsItemLevelsItem";

export type RubricInputDimensionsItem = {
  code: string;
  name: string;
  /** @minItems 2 */
  levels: RubricInputDimensionsItemLevelsItem[];
};
