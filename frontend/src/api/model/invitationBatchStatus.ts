/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type InvitationBatchStatus =
  (typeof InvitationBatchStatus)[keyof typeof InvitationBatchStatus];

export const InvitationBatchStatus = {
  pending_confirmation: "pending_confirmation",
  confirmed: "confirmed",
  expired: "expired",
} as const;
