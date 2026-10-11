/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type SaveItemDraftParams = {
  /**
   * Solo si la versión abierta está En revisión (FR-016): `true` la deja En revisión (la
   * revisión empieza de nuevo); `false` la devuelve a Borrador. Se ignora en otros estados.
   */
  keep_in_review?: boolean;
};
