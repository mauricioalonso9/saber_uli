/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { ItemContent } from "./itemContent";
import type { ItemKind } from "./itemKind";
import type { ModuleCodeValue } from "./moduleCodeValue";

export interface ItemCreate {
  code: BusinessCode;
  module: ModuleCodeValue;
  kind: ItemKind;
  content: ItemContent;
}
