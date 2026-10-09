/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Role } from "./role";

export type AdminSetUserRolesBody = {
  /** @minItems 1 */
  roles: Role[];
  director_program_ids?: string[];
};
