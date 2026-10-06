/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { InvitationBatchRowsItemResult } from "./invitationBatchRowsItemResult";

export type InvitationBatchRowsItem = {
  /** @minimum 1 */
  line: number;
  email: string;
  name?: string;
  access_expires_at?: string;
  result: InvitationBatchRowsItemResult;
  message?: string;
};
