/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { PageParameter } from "./pageParameter";
import type { PageSizeParameter } from "./pageSizeParameter";

export type AdminListGroupMembersParams = {
  /**
   * @minimum 1
   */
  page?: PageParameter;
  /**
   * @minimum 1
   * @maximum 100
   */
  page_size?: PageSizeParameter;
};
