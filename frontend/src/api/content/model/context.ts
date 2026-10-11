/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ContextContent } from "./contextContent";
import type { ContextItemsItem } from "./contextItemsItem";
import type { ContextSummary } from "./contextSummary";
import type { Origin } from "./origin";

export type Context = ContextSummary &
  ContextContent & {
    origin: Origin;
    updated_at: string;
    /** Igual al ETag */
    revision: number;
    items?: ContextItemsItem[];
  };
