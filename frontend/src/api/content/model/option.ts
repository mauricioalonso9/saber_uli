/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface Option {
  /** @pattern ^[A-D]$ */
  key: string;
  /**
   * @minLength 1
   * @maxLength 2000
   */
  text: string;
  correct: boolean;
  /**
   * Obligatoria al enviar a revisión (FR-006)
   * @maxLength 2000
   */
  feedback: string;
}
