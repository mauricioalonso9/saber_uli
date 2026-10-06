/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { GroupStudentProgress } from "./groupStudentProgress";

/**
 * Vista del docente; nunca incluye el correo (FR-027).
 */
export interface GroupStudent {
  user_id: string;
  display_name: string;
  /** Se completa en especificaciones posteriores (003, 008). */
  progress?: GroupStudentProgress;
}
