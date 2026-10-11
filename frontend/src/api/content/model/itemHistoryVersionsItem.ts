/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { UserRef } from "./userRef";
import type { VersionState } from "./versionState";

export type ItemHistoryVersionsItem = {
  number: number;
  state: VersionState;
  author?: UserRef | null;
  reviewer?: UserRef | null;
  created_at: string;
  /** @nullable */
  published_at?: string | null;
  /** @nullable */
  retired_at?: string | null;
  /** Campos que cambiaron frente a la versión anterior */
  changed_fields?: string[];
};
