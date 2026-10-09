/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { InvitationBatchRowsItem } from "./invitationBatchRowsItem";
import type { InvitationBatchStatus } from "./invitationBatchStatus";

export interface InvitationBatch {
  id: string;
  status: InvitationBatchStatus;
  valid_count: number;
  invalid_count: number;
  expires_at: string;
  confirmed_at?: string;
  rows: InvitationBatchRowsItem[];
}
