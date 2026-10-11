/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type VersionState = (typeof VersionState)[keyof typeof VersionState];

export const VersionState = {
  draft: "draft",
  in_review: "in_review",
  published: "published",
  retired: "retired",
} as const;
