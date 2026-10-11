/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ConfirmImportBodyTargetState } from "./confirmImportBodyTargetState";

export type ConfirmImportBody = {
  /** Estado de los ítems nuevos y de las versiones nuevas (los de origen `ia` entran En revisión) */
  target_state: ConfirmImportBodyTargetState;
  /** Los ítems son originales y no reproducen preguntas del ICFES */
  originality_declared: true;
};
