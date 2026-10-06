/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type DeletionRequestOrigin =
  (typeof DeletionRequestOrigin)[keyof typeof DeletionRequestOrigin];

export const DeletionRequestOrigin = {
  user_request: "user_request",
  guest_retention: "guest_retention",
  institutional_retention: "institutional_retention",
} as const;
