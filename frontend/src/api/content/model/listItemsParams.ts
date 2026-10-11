/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Difficulty } from "./difficulty";
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { Origin } from "./origin";
import type { PageParameter } from "./pageParameter";
import type { PageSizeParameter } from "./pageSizeParameter";
import type { ProblemSignal } from "./problemSignal";
import type { VersionState } from "./versionState";

export type ListItemsParams = {
  module?: ModuleCodeValue;
  state?: VersionState;
  origin?: Origin;
  difficulty?: Difficulty;
  /**
   * Categoría de cualquier tipo; incluye sus descendientes
   */
  taxonomy_node?: string;
  /**
   * Señal de problema de las estadísticas (FR-043)
   */
  signal?: ProblemSignal;
  /**
   * En revisión y que quien consulta puede aprobar (cola de revisión)
   */
  awaiting_my_review?: boolean;
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
