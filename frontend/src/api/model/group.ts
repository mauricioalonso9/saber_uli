/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { GroupSummary } from "./groupSummary";
import type { GroupTeachersItem } from "./groupTeachersItem";

export type Group = GroupSummary & {
  description?: string;
  teachers: GroupTeachersItem[];
  archived_at?: string;
  created_at: string;
};
