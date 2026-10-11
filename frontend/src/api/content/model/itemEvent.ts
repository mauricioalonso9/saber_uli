/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ItemEventDetails } from "./itemEventDetails";
import type { ItemEventType } from "./itemEventType";
import type { UserRef } from "./userRef";

export interface ItemEvent {
  id: string;
  type: ItemEventType;
  /** @nullable */
  version?: number | null;
  /** null = sistema */
  actor?: UserRef | null;
  occurred_at: string;
  /** @nullable */
  comment?: string | null;
  /** @nullable */
  reason?: string | null;
  details?: ItemEventDetails;
}
