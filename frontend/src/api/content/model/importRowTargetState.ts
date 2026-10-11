/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

/**
 * Estado con que entraría; `in_review` forzado para origen `ia`
 * @nullable
 */
export type ImportRowTargetState =
  (typeof ImportRowTargetState)[keyof typeof ImportRowTargetState] | null;

export const ImportRowTargetState = {
  draft: "draft",
  in_review: "in_review",
} as const;
