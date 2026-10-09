/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";

export type ImportDetailResult = {
  created: number;
  versioned: number;
  /** Ítems omitidos al confirmar (`changed_since_preview`) */
  skipped: BusinessCode[];
} | null;
