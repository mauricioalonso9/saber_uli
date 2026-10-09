/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type HealthStatusStatus = (typeof HealthStatusStatus)[keyof typeof HealthStatusStatus];

export const HealthStatusStatus = {
  ok: "ok",
  degraded: "degraded",
  unavailable: "unavailable",
} as const;
