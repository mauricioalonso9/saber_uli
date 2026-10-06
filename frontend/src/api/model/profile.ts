/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ProfileDailyGoal } from "./profileDailyGoal";
import type { Program } from "./program";

export interface Profile {
  program?: Program;
  /**
   * @minimum 1
   * @maximum 12
   */
  semester?: number;
  expected_exam_date?: string;
  daily_goal: ProfileDailyGoal;
  /** @maxLength 120 */
  guest_display_name?: string;
  complete: boolean;
}
