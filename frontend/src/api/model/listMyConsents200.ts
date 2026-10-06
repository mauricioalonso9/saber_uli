/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Consent } from "./consent";

export type ListMyConsents200 = {
  current: Consent | null;
  items: Consent[];
};
