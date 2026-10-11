/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ItemCanApproveBlockedReason } from "./itemCanApproveBlockedReason";

/**
 * Acciones que quien consulta puede hacer ahora (para la interfaz)
 */
export type ItemCan = {
  edit: boolean;
  submit: boolean;
  approve: boolean;
  return: boolean;
  reject: boolean;
  retire: boolean;
  /** @nullable */
  approve_blocked_reason?: ItemCanApproveBlockedReason;
};
