/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { PageParameter } from "./pageParameter";
import type { PageSizeParameter } from "./pageSizeParameter";

export type AdminListAuditEventsParams = {
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
   * @maxLength 64
   */
  action?: string;
  actor_id?: string;
  subject_user_id?: string;
  from?: string;
  to?: string;
};
