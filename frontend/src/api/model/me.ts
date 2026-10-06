/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { AccountStatus } from "./accountStatus";
import type { MeAccess } from "./meAccess";
import type { MeKind } from "./meKind";
import type { MeOnboarding } from "./meOnboarding";
import type { Permission } from "./permission";
import type { Role } from "./role";

export interface Me {
  id: string;
  kind: MeKind;
  status: AccountStatus;
  display_name: string;
  email: string;
  roles: Role[];
  permissions: Permission[];
  onboarding: MeOnboarding;
  access: MeAccess;
}
