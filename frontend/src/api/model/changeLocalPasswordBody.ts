/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ChangeLocalPasswordBody = {
  /**
   * @minLength 1
   * @maxLength 128
   */
  current_password: string;
  /**
   * @minLength 1
   * @maxLength 128
   */
  new_password: string;
};
