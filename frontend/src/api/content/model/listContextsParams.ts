/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { PageParameter } from "./pageParameter";
import type { PageSizeParameter } from "./pageSizeParameter";

export type ListContextsParams = {
  module?: ModuleCodeValue;
  /**
   * @maxLength 100
   */
  q?: string;
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
