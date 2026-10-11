/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ProblemSignal = (typeof ProblemSignal)[keyof typeof ProblemSignal];

export const ProblemSignal = {
  too_easy: "too_easy",
  too_hard: "too_hard",
  negative_discrimination: "negative_discrimination",
  distractor_beats_key: "distractor_beats_key",
} as const;
