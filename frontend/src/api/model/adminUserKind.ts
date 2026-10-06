/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type AdminUserKind = (typeof AdminUserKind)[keyof typeof AdminUserKind];

export const AdminUserKind = {
  institutional: "institutional",
  guest: "guest",
} as const;
