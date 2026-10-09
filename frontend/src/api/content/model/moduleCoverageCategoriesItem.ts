/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ModuleCoverageCategoriesItem = {
  node_id: string;
  code: string;
  name: string;
  /** @nullable */
  target_weight?: number | null;
  published: number;
  in_review: number;
  /**
   * @minimum 0
   * @maximum 1
   */
  published_share: number;
  /**
   * Ítems publicados que faltan para el objetivo (`bank_target × target_weight`)
   * @minimum 0
   */
  missing: number;
  below_target: boolean;
};
