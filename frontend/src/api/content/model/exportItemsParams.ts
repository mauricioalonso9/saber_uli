/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Difficulty } from "./difficulty";
import type { ExportItemsFormat } from "./exportItemsFormat";
import type { ExportItemsVersion } from "./exportItemsVersion";
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { Origin } from "./origin";
import type { VersionState } from "./versionState";

export type ExportItemsParams = {
  format: ExportItemsFormat;
  /**
   * Versión de cada ítem que se exporta
   */
  version?: ExportItemsVersion;
  module?: ModuleCodeValue;
  state?: VersionState;
  origin?: Origin;
  difficulty?: Difficulty;
  taxonomy_node?: string;
};
