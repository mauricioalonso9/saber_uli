/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { FieldChange } from "./fieldChange";
import type { ImportAction } from "./importAction";
import type { ImportRowEntity } from "./importRowEntity";
import type { ImportRowErrorsItem } from "./importRowErrorsItem";
import type { ImportRowTargetState } from "./importRowTargetState";

export interface ImportRow {
  /** Código del ítem, consigna o contexto (o "fila N" si falta) */
  code: string;
  entity: ImportRowEntity;
  action: ImportAction;
  /**
   * Estado con que entraría; `in_review` forzado para origen `ia`
   * @nullable
   */
  target_state?: ImportRowTargetState;
  changes?: FieldChange[];
  errors?: ImportRowErrorsItem[];
}
