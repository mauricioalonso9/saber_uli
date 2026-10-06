/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { DeletionRequest } from "./deletionRequest";
import type { PageMeta } from "./pageMeta";

export type DeletionRequestPage = PageMeta & {
  items: DeletionRequest[];
};
