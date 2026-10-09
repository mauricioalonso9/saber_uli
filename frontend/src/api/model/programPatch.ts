/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface ProgramPatch {
  /**
   * @minLength 3
   * @maxLength 200
   */
  name?: string;
  /**
   * @minLength 2
   * @maxLength 100
   */
  campus?: string;
  active?: boolean;
}
