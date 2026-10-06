/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ConsentDecision = (typeof ConsentDecision)[keyof typeof ConsentDecision];

export const ConsentDecision = {
  accepted: "accepted",
  rejected: "rejected",
  revoked: "revoked",
} as const;
