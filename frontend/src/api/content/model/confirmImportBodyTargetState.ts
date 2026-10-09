/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

/**
 * Estado de los ítems nuevos y de las versiones nuevas (los de origen `ia` entran En revisión)
 */
export type ConfirmImportBodyTargetState =
  (typeof ConfirmImportBodyTargetState)[keyof typeof ConfirmImportBodyTargetState];

export const ConfirmImportBodyTargetState = {
  draft: "draft",
  in_review: "in_review",
} as const;
