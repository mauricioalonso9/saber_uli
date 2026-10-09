/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type TaxonomyNodeKind = (typeof TaxonomyNodeKind)[keyof typeof TaxonomyNodeKind];

export const TaxonomyNodeKind = {
  competence: "competence",
  assertion: "assertion",
  evidence: "evidence",
  component: "component",
  situation: "situation",
  text_type: "text_type",
  part: "part",
} as const;
