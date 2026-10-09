/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type InvitationStatus = (typeof InvitationStatus)[keyof typeof InvitationStatus];

export const InvitationStatus = {
  sent: "sent",
  accepted: "accepted",
  expired: "expired",
  revoked: "revoked",
} as const;
