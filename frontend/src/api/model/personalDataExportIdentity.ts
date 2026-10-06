/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type PersonalDataExportIdentity = {
  id?: string;
  kind?: string;
  display_name?: string;
  email?: string;
  created_at?: string;
  last_login_at?: string;
  /** Explica que nombre y correo institucionales se corrigen en el directorio de Unilibre (escenario 8.2) */
  source_note?: string;
};
