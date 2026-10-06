/**
 * Guardias de navegación (FR-014, FR-019 a FR-022, FR-030, FR-039; research R-35).
 *
 * `decideNavigation` es una función pura: recibe el estado de la sesión y la ruta pedida y
 * devuelve a dónde redirigir, o `null` si la ruta se puede mostrar. El orden refleja el primer
 * ingreso (FR-022): autorización de datos → perfil → aplicación. Las rutas de docente y de
 * administración exigen el permiso del contrato; sin él se vuelve a `/inicio` (la API responde
 * igualmente 403: la guardia solo evita mostrar pantallas inútiles).
 */
import type { Me, Permission } from "@/api/model";

export type SessionState =
  { kind: "anonymous" } | { kind: "offline-expired" } | { kind: "authenticated"; me: Me };

export const PUBLIC_PATHS = ["/ingresar", "/acceso"] as const;
export const CONSENT_PATH = "/bienvenida/datos";
export const PROFILE_PATH = "/bienvenida/perfil";
export const OFFLINE_PATH = "/sin-conexion";
export const HOME_PATH = "/inicio";
export const LOGIN_PATH = "/ingresar";

/** Prefijo de ruta → permisos que la habilitan (basta uno). */
const ROUTE_PERMISSIONS: ReadonlyArray<readonly [string, readonly Permission[]]> = [
  ["/invitaciones", ["invitations:manage_own", "invitations:manage_all"]],
  ["/grupos", ["groups:read_own_students"]],
  ["/admin/usuarios", ["users:manage"]],
  ["/admin/grupos", ["groups:manage"]],
  ["/admin/programas", ["programs:manage"]],
  ["/admin/supresiones", ["deletions:read"]],
  ["/admin/politica", ["policy:publish"]],
  ["/admin/parametros", ["settings:manage"]],
  ["/admin/auditoria", ["audit:read"]],
];

function matches(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

function isPublic(path: string): boolean {
  return PUBLIC_PATHS.some((prefix) => matches(path, prefix));
}

export function requiredPermissions(path: string): readonly Permission[] | null {
  const entry = ROUTE_PERMISSIONS.find(([prefix]) => matches(path, prefix));
  return entry ? entry[1] : null;
}

export function decideNavigation(session: SessionState, path: string): string | null {
  if (session.kind === "offline-expired") {
    return path === OFFLINE_PATH ? null : OFFLINE_PATH;
  }
  if (session.kind === "anonymous") {
    return isPublic(path) ? null : `${LOGIN_PATH}?return_to=${encodeURIComponent(path)}`;
  }

  const { onboarding, permissions } = session.me;
  if (onboarding.consent_required) {
    return path === CONSENT_PATH ? null : CONSENT_PATH;
  }
  if (onboarding.profile_required) {
    return path === PROFILE_PATH ? null : PROFILE_PATH;
  }
  if (isPublic(path) || path === CONSENT_PATH || path === PROFILE_PATH || path === OFFLINE_PATH) {
    return HOME_PATH;
  }
  const required = requiredPermissions(path);
  if (required && !required.some((permission) => permissions.includes(permission))) {
    return HOME_PATH;
  }
  return null;
}
