/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ItemKind = (typeof ItemKind)[keyof typeof ItemKind];

export const ItemKind = {
  selection: "selection",
  matching: "matching",
  writing_prompt: "writing_prompt",
} as const;
