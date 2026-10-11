/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface SharedOption {
  /** @pattern ^[A-H]$ */
  key: string;
  /**
   * @minLength 1
   * @maxLength 500
   */
  text: string;
  /**
   * @minLength 1
   * @maxLength 2000
   */
  feedback: string;
}
