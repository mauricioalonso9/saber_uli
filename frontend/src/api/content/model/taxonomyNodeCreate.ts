/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { TaxonomyNodeCreatePartFormat } from "./taxonomyNodeCreatePartFormat";
import type { TaxonomyNodeKind } from "./taxonomyNodeKind";

export interface TaxonomyNodeCreate {
  module: ModuleCodeValue;
  kind: TaxonomyNodeKind;
  /** @pattern ^[A-Z]{2,3}-[A-Z0-9.-]{1,20}$ */
  code: string;
  /**
   * @minLength 1
   * @maxLength 200
   */
  name: string;
  /** @maxLength 1000 */
  description?: string;
  parent_id?: string;
  /**
   * @minimum 0
   * @maximum 1
   */
  target_weight?: number;
  /**
   * @minimum 2
   * @maximum 8
   */
  part_options?: number;
  part_format?: TaxonomyNodeCreatePartFormat;
}
