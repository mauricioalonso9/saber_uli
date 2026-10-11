/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { BusinessCode } from "./businessCode";
import type { ContextContent } from "./contextContent";
import type { ModuleCodeValue } from "./moduleCodeValue";

export type ContextCreate = ContextContent & {
  code: BusinessCode;
  module: ModuleCodeValue;
};
