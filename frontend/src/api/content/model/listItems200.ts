/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ItemSummary } from "./itemSummary";
import type { PageMeta } from "./pageMeta";

export type ListItems200 = {
  items: ItemSummary[];
  meta: PageMeta;
};
