/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ImportDetailResult } from "./importDetailResult";
import type { ImportRow } from "./importRow";
import type { ImportSummary } from "./importSummary";
import type { PageMeta } from "./pageMeta";

export type ImportDetail = ImportSummary & {
  rows: ImportRow[];
  meta: PageMeta;
  result?: ImportDetailResult;
};
