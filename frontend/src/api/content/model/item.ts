/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { ItemCan } from "./itemCan";
import type { ItemKind } from "./itemKind";
import type { ItemVersion } from "./itemVersion";
import type { ModuleCodeValue } from "./moduleCodeValue";
import type { Origin } from "./origin";

export interface Item {
  code: BusinessCode;
  module: ModuleCodeValue;
  kind: ItemKind;
  origin: Origin;
  /** Igual al ETag (R-09) */
  revision: number;
  published: ItemVersion | null;
  open: ItemVersion | null;
  /**
   * Comentario de la última devolución
   * @nullable
   */
  last_review_comment?: string | null;
  /** Acciones que quien consulta puede hacer ahora (para la interfaz) */
  can: ItemCan;
}
