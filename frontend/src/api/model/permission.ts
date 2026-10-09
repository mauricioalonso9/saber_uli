/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type Permission = (typeof Permission)[keyof typeof Permission];

export const Permission = {
  "invitations:manage_own": "invitations:manage_own",
  "invitations:manage_all": "invitations:manage_all",
  "users:manage": "users:manage",
  "groups:manage": "groups:manage",
  "groups:read_own_students": "groups:read_own_students",
  "programs:read_aggregated": "programs:read_aggregated",
  "programs:manage": "programs:manage",
  "settings:manage": "settings:manage",
  "audit:read": "audit:read",
  "policy:publish": "policy:publish",
  "deletions:read": "deletions:read",
} as const;
