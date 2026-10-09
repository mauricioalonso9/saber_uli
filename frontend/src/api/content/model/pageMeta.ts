/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface PageMeta {
  /** @minimum 1 */
  page: number;
  /**
   * @minimum 1
   * @maximum 100
   */
  page_size: number;
  /** @minimum 0 */
  total: number;
}
