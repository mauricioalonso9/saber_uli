/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { PersonalDataSessionAuthMethod } from "./personalDataSessionAuthMethod";

export interface PersonalDataSession {
  auth_method: PersonalDataSessionAuthMethod;
  started_at: string;
  last_seen_at: string;
  expires_at: string;
  revoked_at?: string;
}
