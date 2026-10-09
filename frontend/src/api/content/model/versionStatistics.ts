/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ProblemSignal } from "./problemSignal";
import type { VersionStatisticsOptionRates } from "./versionStatisticsOptionRates";
import type { VersionStatisticsState } from "./versionStatisticsState";

export interface VersionStatistics {
  version: number;
  state: VersionStatisticsState;
  /** @minimum 0 */
  first_responses: number;
  /** false con menos de 30 respuestas (FR-042) */
  sufficient_data: boolean;
  /**
   * @minimum 0
   * @maximum 1
   * @nullable
   */
  correct_rate?: number | null;
  /** @nullable */
  option_rates?: VersionStatisticsOptionRates;
  /**
   * @minimum -1
   * @maximum 1
   * @nullable
   */
  discrimination?: number | null;
  signals: ProblemSignal[];
  /** @nullable */
  computed_at?: string | null;
}
