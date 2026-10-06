/**
 * Llamadas directas a la API como un usuario autenticado (por ejemplo, un administrador que
 * prepara datos). El token se obtiene en el navegador tras el ingreso (`signInWithMicrosoft`) y se
 * renueva con la cookie `su_refresh` de esa página.
 */
import { type APIRequestContext, type Page, request } from "@playwright/test";

const API_URL = process.env.E2E_BASE_URL ?? "http://localhost";

/** Pide un token de acceso con la cookie de la página (misma sesión que el navegador). */
export async function accessTokenFrom(page: Page): Promise<string> {
  const response = await page.request.post("/api/auth/refresh", {
    headers: { "X-Requested-With": "saber-uli" },
  });
  if (!response.ok()) {
    throw new Error(`no se pudo renovar la sesión (${response.status()})`);
  }
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

export async function apiAs(token: string): Promise<APIRequestContext> {
  return request.newContext({
    baseURL: API_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${token}`, "X-Requested-With": "saber-uli" },
  });
}
