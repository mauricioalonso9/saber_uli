/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type PersonalDataAuditEventActor =
  (typeof PersonalDataAuditEventActor)[keyof typeof PersonalDataAuditEventActor];

export const PersonalDataAuditEventActor = {
  self: "self",
  staff: "staff",
  system: "system",
} as const;
