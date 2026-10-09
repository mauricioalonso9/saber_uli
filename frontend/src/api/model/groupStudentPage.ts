/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { GroupStudent } from "./groupStudent";
import type { PageMeta } from "./pageMeta";

export type GroupStudentPage = PageMeta & {
  items: GroupStudent[];
};
