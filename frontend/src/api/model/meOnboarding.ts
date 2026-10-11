/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type MeOnboarding = {
  consent_required: boolean;
  current_policy_version_id?: string;
  profile_required: boolean;
  /** La cuenta local debe cambiar su contraseña antes de cualquier otra cosa (FR-041) */
  password_change_required: boolean;
};
