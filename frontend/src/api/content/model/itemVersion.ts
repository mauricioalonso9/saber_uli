/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ItemContent } from "./itemContent";
import type { ItemVersionContentIssuesItem } from "./itemVersionContentIssuesItem";
import type { UserRef } from "./userRef";
import type { VersionState } from "./versionState";

export interface ItemVersion {
  /** @minimum 1 */
  number: number;
  state: VersionState;
  content: ItemContent;
  /**
   * Versión del contexto que fija (R-02)
   * @nullable
   */
  context_version?: number | null;
  /** Problemas que impiden enviarla a revisión (vacío si está completa) */
  content_issues: ItemVersionContentIssuesItem[];
  author: UserRef | null;
  contributors: UserRef[];
  reviewer?: UserRef | null;
  created_at: string;
  /** @nullable */
  submitted_at?: string | null;
  /** @nullable */
  published_at?: string | null;
  /** @nullable */
  retired_at?: string | null;
  /** @nullable */
  retire_reason?: string | null;
}
