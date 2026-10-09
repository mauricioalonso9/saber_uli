/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { TaxonomyNodeKind } from "./taxonomyNodeKind";
import type { TaxonomyNodePartFormat } from "./taxonomyNodePartFormat";

export interface TaxonomyNode {
  id: string;
  module: ModuleCodeValue;
  kind: TaxonomyNodeKind;
  code: string;
  name: string;
  /** @nullable */
  description?: string | null;
  /** @nullable */
  parent_id?: string | null;
  /**
   * @minimum 0
   * @maximum 1
   * @nullable
   */
  target_weight?: number | null;
  /** @nullable */
  part_options?: number | null;
  /** @nullable */
  part_format?: TaxonomyNodePartFormat;
  active: boolean;
  /** La usa algún ítem o contexto (no se puede borrar) */
  in_use: boolean;
  warnings?: string[];
}
