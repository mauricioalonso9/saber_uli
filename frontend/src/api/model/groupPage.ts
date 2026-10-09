/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Group } from "./group";
import type { PageMeta } from "./pageMeta";

export type GroupPage = PageMeta & {
  items: Group[];
};
