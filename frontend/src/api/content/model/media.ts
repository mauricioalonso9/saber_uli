/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { MediaContentType } from "./mediaContentType";

export interface Media {
  id: string;
  content_type: MediaContentType;
  width: number;
  height: number;
  size_bytes: number;
  /** Ruta de `getContentMedia` */
  url: string;
}
