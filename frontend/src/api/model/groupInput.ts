/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface GroupInput {
  /**
   * @minLength 2
   * @maxLength 120
   */
  name: string;
  /** @maxLength 500 */
  description?: string;
  /** @maxLength 20 */
  cohort_label?: string;
  program_id?: string;
}
