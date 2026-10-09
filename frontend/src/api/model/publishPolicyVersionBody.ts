/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type PublishPolicyVersionBody = {
  /** @pattern ^[0-9]+\.[0-9]+$ */
  version: string;
  /** @maxLength 200 */
  title: string;
  /**
   * @minLength 200
   * @maxLength 100000
   */
  body_markdown: string;
  effective_from: string;
};
