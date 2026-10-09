/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { DecideConsentBodyDecision } from "./decideConsentBodyDecision";

export type DecideConsentBody = {
  policy_version_id: string;
  decision: DecideConsentBodyDecision;
};
