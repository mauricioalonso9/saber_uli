/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { Difficulty } from "./difficulty";
import type { ItemKind } from "./itemKind";
import type { ItemSummaryOpenVersion } from "./itemSummaryOpenVersion";
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { Origin } from "./origin";
import type { ProblemSignal } from "./problemSignal";

export interface ItemSummary {
  code: BusinessCode;
  module: ModuleCodeValue;
  kind: ItemKind;
  origin: Origin;
  difficulty: Difficulty;
  /** @maxLength 160 */
  stem_excerpt: string;
  context_code?: BusinessCode | null;
  /** @nullable */
  assertion_code?: string | null;
  /** @nullable */
  part_code?: string | null;
  /** @nullable */
  published_version: number | null;
  open_version: ItemSummaryOpenVersion;
  /** Todas sus versiones están Retiradas */
  retired?: boolean;
  /** Ningún administrador disponible puede aprobarla (todos la modificaron) */
  needs_another_reviewer?: boolean;
  signals?: ProblemSignal[];
  updated_at: string;
}
