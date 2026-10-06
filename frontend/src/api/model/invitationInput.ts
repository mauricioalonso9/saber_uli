/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface InvitationInput {
  /** @maxLength 254 */
  email: string;
  /** @maxLength 120 */
  invitee_name?: string;
  /** Si se omite, se usa `default_guest_access_days`. */
  access_expires_at?: string;
}
