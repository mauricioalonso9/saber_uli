/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface TaxonomyNodeUpdate {
  /**
   * @minLength 1
   * @maxLength 200
   */
  name?: string;
  /**
   * @maxLength 1000
   * @nullable
   */
  description?: string | null;
  /**
   * @minimum 0
   * @maximum 1
   * @nullable
   */
  target_weight?: number | null;
  active?: boolean;
}
