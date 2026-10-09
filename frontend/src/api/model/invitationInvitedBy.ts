/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

/**
 * `null` si la creó el sistema (comando de operación invite-guest). `display_name` es
 * `null` si quien invitó fue suprimido.
 * @nullable
 */
export type InvitationInvitedBy = {
  id: string;
  /** @nullable */
  display_name?: string | null;
} | null;
