/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

/**
 * Vista del administrador (a diferencia de `GroupStudent`, incluye el correo).
 */
export interface GroupMember {
  user_id: string;
  /** @nullable */
  display_name: string | null;
  /** @nullable */
  email?: string | null;
}
