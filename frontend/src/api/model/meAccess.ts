/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type MeAccess = {
  valid: boolean;
  validated_at: string;
  /** validated_at + 7 días (FR-038) */
  offline_grace_until: string;
  guest_access_expires_at?: string;
  privileged_session?: boolean;
};
