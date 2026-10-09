/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ContextSummary } from "./contextSummary";
import type { PageMeta } from "./pageMeta";

export type ListContexts200 = {
  items: ContextSummary[];
  meta: PageMeta;
};
