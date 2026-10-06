/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type DeletionRequestStatus =
  (typeof DeletionRequestStatus)[keyof typeof DeletionRequestStatus];

export const DeletionRequestStatus = {
  received: "received",
  in_progress: "in_progress",
  completed: "completed",
} as const;
