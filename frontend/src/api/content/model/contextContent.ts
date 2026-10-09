/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ContextContentKind } from "./contextContentKind";
import type { SharedOption } from "./sharedOption";

/**
 * Sin `additionalProperties: false` porque `ContextCreate` y `Context` lo combinan con otros
 * campos (`allOf`); el servidor rechaza los campos desconocidos con 422 `validation-error`.
 */
export interface ContextContent {
  kind: ContextContentKind;
  /**
   * @minLength 1
   * @maxLength 200
   */
  title: string;
  /**
   * @maxLength 20000
   * @nullable
   */
  body_md?: string | null;
  /** @nullable */
  media_id?: string | null;
  /**
   * @maxLength 1000
   * @nullable
   */
  alt_text?: string | null;
  /** @nullable */
  text_type_node_id?: string | null;
  /** @nullable */
  part_node_id?: string | null;
  /**
   * @maxLength 60
   * @nullable
   */
  subtype?: string | null;
  /**
   * El dominio exige exactamente `part_options` de la parte (8 en la parte 1, FR-003)
   * @minItems 2
   * @maxItems 8
   * @nullable
   */
  shared_options?: SharedOption[] | null;
}
