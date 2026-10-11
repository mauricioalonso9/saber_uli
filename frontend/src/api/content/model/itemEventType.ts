/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ItemEventType = (typeof ItemEventType)[keyof typeof ItemEventType];

export const ItemEventType = {
  created: "created",
  edited: "edited",
  submitted: "submitted",
  approved: "approved",
  returned: "returned",
  rejected: "rejected",
  retired: "retired",
  superseded: "superseded",
  commented: "commented",
  imported: "imported",
  seed_loaded: "seed_loaded",
  seed_versioned: "seed_versioned",
  context_changed: "context_changed",
  rebased_on_context: "rebased_on_context",
} as const;
