/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type InvitationBatchRowsItemResult =
  (typeof InvitationBatchRowsItemResult)[keyof typeof InvitationBatchRowsItemResult];

export const InvitationBatchRowsItemResult = {
  valid: "valid",
  invalid_email: "invalid_email",
  duplicate_in_file: "duplicate_in_file",
  already_invited: "already_invited",
  institutional_email: "institutional_email",
  expiry_out_of_range: "expiry_out_of_range",
} as const;
