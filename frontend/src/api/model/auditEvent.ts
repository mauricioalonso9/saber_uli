/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { AuditEventDetails } from "./auditEventDetails";

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_id?: string | null;
  action: string;
  target_type: string;
  target_id?: string;
  subject_user_id?: string;
  details?: AuditEventDetails;
}
