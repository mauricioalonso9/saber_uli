/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Consent } from "./consent";
import type { PersonalDataAuditEvent } from "./personalDataAuditEvent";
import type { PersonalDataExportIdentity } from "./personalDataExportIdentity";
import type { PersonalDataExportInvitation } from "./personalDataExportInvitation";
import type { PersonalDataExportSections } from "./personalDataExportSections";
import type { PersonalDataSession } from "./personalDataSession";
import type { Profile } from "./profile";
import type { Program } from "./program";
import type { Role } from "./role";

export interface PersonalDataExport {
  generated_at: string;
  identity: PersonalDataExportIdentity;
  profile?: Profile;
  roles: Role[];
  groups?: string[];
  consents: Consent[];
  /** Solo invitados */
  invitation?: PersonalDataExportInvitation;
  /** Programas que dirige (solo con el rol Director de programa) */
  director_programs?: Program[];
  /** Sesiones de la persona, de la más reciente a la más antigua */
  sessions?: PersonalDataSession[];
  /**
   * Eventos de auditoría sobre la persona, del más reciente al más antiguo. No identifican
   * a quien hizo la acción: `actor` dice solo si fue la persona, el personal o el sistema.
   */
  audit_events?: PersonalDataAuditEvent[];
  /** Secciones agregadas por otros contextos en especificaciones futuras */
  sections?: PersonalDataExportSections;
}
