/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type ImportSummaryStatus = (typeof ImportSummaryStatus)[keyof typeof ImportSummaryStatus];

export const ImportSummaryStatus = {
  pending: "pending",
  confirmed: "confirmed",
  expired: "expired",
} as const;
