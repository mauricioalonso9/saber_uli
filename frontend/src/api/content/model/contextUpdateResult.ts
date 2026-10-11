/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { Context } from "./context";

export interface ContextUpdateResult {
  context: Context;
  /** Ítems publicados que recibieron una versión nueva En revisión (FR-020) */
  new_review_versions: BusinessCode[];
  /** Versiones abiertas que pasaron a la nueva versión del contexto */
  rebased_open_versions: BusinessCode[];
}
