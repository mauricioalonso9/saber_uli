/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { PageMeta } from "./pageMeta";
import type { Program } from "./program";

export type ProgramPage = PageMeta & {
  items: Program[];
};
