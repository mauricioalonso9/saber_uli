/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { Problem } from "./problem";

/**
 * Sin sesión válida. `type`: `unauthenticated`, `session-revoked`, `account-disabled`,
 * `guest-access-expired`, `guest-access-revoked` o `reauthentication-required`.
 */
export type UnauthorizedResponse = Problem;
