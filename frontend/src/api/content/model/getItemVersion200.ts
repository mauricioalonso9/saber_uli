/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { FieldChange } from "./fieldChange";
import type { ItemVersion } from "./itemVersion";

export type GetItemVersion200 = {
  version: ItemVersion;
  /** Vacío en la versión 1 */
  changes: FieldChange[];
};
