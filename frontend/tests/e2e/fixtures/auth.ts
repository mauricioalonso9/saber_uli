/**
 * Ingreso con el proveedor OIDC simulado (`mock-oauth2-server`, perfil e2e).
 *
 * El formulario interactivo del simulador pide un usuario y, opcionalmente, claims en JSON. El
 * usuario se usa como `oid` (`infra/docker/mock-oauth2.json`); para simular una cuenta de otro
 * inquilino se envía `tid` externo en los claims (escenario de rechazo, FR-002).
 */
import { type Page, expect } from "@playwright/test";

export const TENANT_ID = process.env.E2E_TENANT_ID ?? "11111111-1111-4111-8111-111111111111";
export const EXTERNAL_TENANT_ID =
  process.env.E2E_EXTERNAL_TENANT_ID ?? "22222222-2222-4222-8222-222222222222";

export interface MockUser {
  /** GUID que el simulador emite como `oid`. */
  oid: string;
  email?: string;
  name?: string;
  external?: boolean;
}

export function newMockUser(overrides: Partial<MockUser> = {}): MockUser {
  return { oid: crypto.randomUUID(), ...overrides };
}

/** Pulsa "Ingresar con mi cuenta Unilibre" y completa el formulario del simulador. */
export async function signInWithMicrosoft(page: Page, user: MockUser): Promise<void> {
  await page.goto("/ingresar");
  await page.getByRole("button", { name: "Ingresar con mi cuenta Unilibre" }).click();

  await expect(page).toHaveURL(/oidc:8080/);
  await page.locator("input[name=username]").fill(user.oid);
  const claims: Record<string, string> = {};
  if (user.email) claims.email = user.email;
  if (user.name) claims.name = user.name;
  if (user.external) claims.tid = EXTERNAL_TENANT_ID;
  if (Object.keys(claims).length > 0) {
    await page.locator("textarea[name=claims]").fill(JSON.stringify(claims));
  }
  await page.locator("input[type=submit]").click();
}
