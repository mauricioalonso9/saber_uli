/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ImportAction = (typeof ImportAction)[keyof typeof ImportAction];

export const ImportAction = {
  create: "create",
  update: "update",
  unchanged: "unchanged",
  error: "error",
} as const;
