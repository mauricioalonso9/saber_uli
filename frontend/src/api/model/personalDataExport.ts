/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Consent } from "./consent";
import type { PersonalDataExportIdentity } from "./personalDataExportIdentity";
import type { PersonalDataExportInvitation } from "./personalDataExportInvitation";
import type { PersonalDataExportSections } from "./personalDataExportSections";
import type { Profile } from "./profile";
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
  /** Secciones agregadas por otros contextos en especificaciones futuras */
  sections?: PersonalDataExportSections;
}
