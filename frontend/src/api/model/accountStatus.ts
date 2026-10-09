/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

/**
 * Estado visible, combinación del estado de la cuenta y del acceso de invitado.
 */
export type AccountStatus = (typeof AccountStatus)[keyof typeof AccountStatus];

export const AccountStatus = {
  active: "active",
  disabled: "disabled",
  guest_expired: "guest_expired",
  guest_revoked: "guest_revoked",
  deletion_pending: "deletion_pending",
  deleted: "deleted",
} as const;
