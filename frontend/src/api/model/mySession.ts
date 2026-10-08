/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { MySessionAuthMethod } from "./mySessionAuthMethod";

export interface MySession {
  id: string;
  auth_method: MySessionAuthMethod;
  started_at: string;
  last_activity_at: string;
  /** Es la sesión de esta petición */
  current: boolean;
}
