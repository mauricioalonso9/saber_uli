/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ProfileUpdateDailyGoal } from "./profileUpdateDailyGoal";

/**
 * Institucional: `program_id`, `semester`, `expected_exam_date` y `daily_goal` son
 * obligatorios. Invitado: `guest_display_name` y `daily_goal` obligatorios;
 * `expected_exam_date` opcional; `program_id` y `semester` no se aceptan.
 */
export interface ProfileUpdate {
  program_id?: string;
  /**
   * @minimum 1
   * @maximum 12
   */
  semester?: number;
  expected_exam_date?: string;
  daily_goal: ProfileUpdateDailyGoal;
  /**
   * @minLength 2
   * @maxLength 120
   */
  guest_display_name?: string;
}
