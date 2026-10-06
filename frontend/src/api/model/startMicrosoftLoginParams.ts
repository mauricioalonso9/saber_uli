/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type StartMicrosoftLoginParams = {
  /**
   * Ruta interna a la que volver tras el ingreso. Solo rutas relativas.
   * @maxLength 200
   * @pattern ^/[^/].*$
   */
  return_to?: string;
};
