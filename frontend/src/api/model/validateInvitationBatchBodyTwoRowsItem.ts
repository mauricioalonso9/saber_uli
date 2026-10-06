/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ValidateInvitationBatchBodyTwoRowsItem = {
  /** @maxLength 254 */
  email: string;
  /** @maxLength 120 */
  name?: string;
  access_expires_at?: string;
};
