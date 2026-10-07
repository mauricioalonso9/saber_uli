/**
 * Arranque y fin de la sesión en el frontend (T080; escenario 1.4).
 *
 * - Ingreso institucional: navegación completa a `/api/auth/microsoft/login` (el backend hace el
 *   flujo OIDC y vuelve con la cookie `su_refresh`). Al volver, el cargador de sesión de las
 *   guardias (`session-loader.ts`) renueva, consulta `/me`, guarda la instantánea y redirige.
 * - Cierre de sesión: revoca la sesión en el servidor y borra el token en memoria y la
 *   instantánea sin conexión, aunque el servidor no responda.
 */
import { useSessionStore } from "@/features/auth/session-store";
import { clearOfflineSnapshot } from "@/features/auth/offline-access";
import { customInstance } from "@/shared/api/http";

/** Envoltorio de la navegación completa (se sustituye en las pruebas). */
export const browser = {
  assign(url: string): void {
    window.location.assign(url);
  },
};

export function microsoftLoginUrl(returnTo?: string | null): string {
  const base = "/api/auth/microsoft/login";
  return returnTo ? `${base}?return_to=${encodeURIComponent(returnTo)}` : base;
}

export function startMicrosoftLogin(returnTo?: string | null): void {
  browser.assign(microsoftLoginUrl(returnTo));
}

export async function logout(): Promise<void> {
  try {
    await customInstance<void>("/api/auth/logout", { method: "POST" });
  } catch {
    // Sin conexión o sesión ya cerrada: igual se borra todo lo local.
  } finally {
    useSessionStore.getState().clear();
    await clearOfflineSnapshot();
  }
}
