/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export interface SessionTokens {
  access_token: string;
  token_type: "Bearer";
  /** Segundos (600) */
  expires_in: number;
}
