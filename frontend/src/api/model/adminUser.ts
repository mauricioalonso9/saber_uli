/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { AccountStatus } from "./accountStatus";
import type { AdminUserKind } from "./adminUserKind";
import type { Program } from "./program";
import type { Role } from "./role";

/**
 * Las cuentas en estado `deleted` no tienen datos personales (`display_name` y `email` son `null`).
 */
export interface AdminUser {
  id: string;
  kind: AdminUserKind;
  status: AccountStatus;
  /** @nullable */
  display_name?: string | null;
  /** @nullable */
  email?: string | null;
  roles: Role[];
  director_programs?: Program[];
  last_login_at?: string;
  retention_deletion_on?: string;
  created_at: string;
}
