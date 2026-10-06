/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { HealthStatusChecks } from "./healthStatusChecks";
import type { HealthStatusStatus } from "./healthStatusStatus";

export interface HealthStatus {
  status: HealthStatusStatus;
  checks?: HealthStatusChecks;
}
