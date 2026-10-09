/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { AccountStatus } from "./accountStatus";
import type { AdminListUsersKind } from "./adminListUsersKind";
import type { PageParameter } from "./pageParameter";
import type { PageSizeParameter } from "./pageSizeParameter";
import type { Role } from "./role";

export type AdminListUsersParams = {
  /**
   * @minimum 1
   */
  page?: PageParameter;
  /**
   * @minimum 1
   * @maximum 100
   */
  page_size?: PageSizeParameter;
  /**
   * @maxLength 254
   */
  q?: string;
  kind?: AdminListUsersKind;
  role?: Role;
  status?: AccountStatus;
};
