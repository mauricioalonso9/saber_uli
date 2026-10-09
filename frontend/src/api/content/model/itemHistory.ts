/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ItemEvent } from "./itemEvent";
import type { ItemHistoryVersionsItem } from "./itemHistoryVersionsItem";

export interface ItemHistory {
  versions: ItemHistoryVersionsItem[];
  events: ItemEvent[];
}
