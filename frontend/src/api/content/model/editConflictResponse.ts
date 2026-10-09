/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { EditConflictResponseCurrent } from "./editConflictResponseCurrent";
import type { Problem } from "./problem";

export type EditConflictResponse = Problem & {
  /** `Item` o `Context` actual */
  current?: EditConflictResponseCurrent;
  etag?: string;
};
