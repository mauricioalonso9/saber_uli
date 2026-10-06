/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ConsentDecision } from "./consentDecision";

export interface Consent {
  id: string;
  policy_version_id: string;
  policy_version: string;
  decision: ConsentDecision;
  channel: string;
  decided_at: string;
}
