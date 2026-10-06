/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { DeletionRequestOrigin } from "./deletionRequestOrigin";
import type { DeletionRequestStatus } from "./deletionRequestStatus";

export interface DeletionRequest {
  id: string;
  /** Solo en vistas de administrador */
  user_id?: string;
  status: DeletionRequestStatus;
  origin: DeletionRequestOrigin;
  requested_at: string;
  due_date: string;
  completed_at?: string;
}
