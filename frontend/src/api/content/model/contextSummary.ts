/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { ContextSummaryKind } from "./contextSummaryKind";
import type { ModuleCodeValue } from "./moduleCodeValue";

export interface ContextSummary {
  code: BusinessCode;
  module: ModuleCodeValue;
  kind: ContextSummaryKind;
  title: string;
  version: number;
  /** @nullable */
  word_count?: number | null;
  /** Ítems que lo usan (FR-026) */
  item_count: number;
  published_item_count: number;
}
