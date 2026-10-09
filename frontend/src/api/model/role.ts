/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type Role = (typeof Role)[keyof typeof Role];

export const Role = {
  student: "student",
  guest: "guest",
  teacher: "teacher",
  program_director: "program_director",
  admin: "admin",
} as const;
