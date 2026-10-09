/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ApproveItemBody = {
  /** Verificó la alineación con la guía del ICFES (FR-014) */
  confirms_alignment: true;
  /** No reproduce preguntas del ICFES (FR-014) */
  confirms_originality: true;
};
