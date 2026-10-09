/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type MySessionAuthMethod = (typeof MySessionAuthMethod)[keyof typeof MySessionAuthMethod];

export const MySessionAuthMethod = {
  entra_id: "entra_id",
  guest_link: "guest_link",
} as const;
