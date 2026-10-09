/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { PersonalDataAuditEventActor } from "./personalDataAuditEventActor";
import type { PersonalDataAuditEventDetails } from "./personalDataAuditEventDetails";

export interface PersonalDataAuditEvent {
  occurred_at: string;
  action: string;
  actor: PersonalDataAuditEventActor;
  details?: PersonalDataAuditEventDetails;
}
