/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ImportSummaryCounts } from "./importSummaryCounts";
import type { ImportSummaryFormat } from "./importSummaryFormat";
import type { ImportSummaryStatus } from "./importSummaryStatus";
import type { UserRef } from "./userRef";

export interface ImportSummary {
  id: string;
  status: ImportSummaryStatus;
  source_name: string;
  format: ImportSummaryFormat;
  created_at: string;
  expires_at: string;
  /** @nullable */
  confirmed_at?: string | null;
  created_by: UserRef;
  counts: ImportSummaryCounts;
}
