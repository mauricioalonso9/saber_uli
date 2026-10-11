/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { ModuleCoverageCategoriesItem } from "./moduleCoverageCategoriesItem";
import type { TaxonomyNodeKind } from "./taxonomyNodeKind";

export interface ModuleCoverage {
  module: ModuleCodeValue;
  grouped_by: TaxonomyNodeKind;
  bank_target: number;
  published_total: number;
  in_review_total: number;
  categories: ModuleCoverageCategoriesItem[];
}
