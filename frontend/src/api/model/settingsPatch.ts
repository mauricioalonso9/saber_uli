/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface SettingsPatch {
  /**
   * @minimum 1
   * @maximum 730
   */
  teacher_max_access_days?: number;
  /**
   * @minimum 1
   * @maximum 730
   */
  default_guest_access_days?: number;
  /**
   * @minimum 1
   * @maximum 30
   */
  invitation_link_ttl_days?: number;
  /**
   * @minimum 5
   * @maximum 10
   */
  sign_in_link_ttl_minutes?: number;
}
