/**
 * T164: supresión voluntaria contra el stack con perfil e2e (US7; quickstart V18; FR-032 a
 * FR-034; SC-006). El worker procesa la solicitud por el outbox; reingresar con la misma cuenta
 * crea una cuenta nueva, sin historial.
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { accessTokenFrom, apiAs } from "./fixtures/api";
import { type MockUser, newMockUser, signInWithMicrosoft } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { deletionRequestStatus, grantRole } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test.describe.configure({ timeout: 120_000 });

async function person(browser: Browser, name: string): Promise<{ page: Page; user: MockUser }> {
  const page = await (await browser.newContext()).newPage();
  const user = await onboardedUser(page, { ...newMockUser(), name });
  return { page, user };
}

async function myId(page: Page): Promise<string> {
  const api = await apiAs(await accessTokenFrom(page));
  const me = (await (await api.get("/api/v1/me")).json()) as { id: string };
  await api.dispose();
  return me.id;
}

test("V18: supresión voluntaria con cierre inmediato y reingreso como cuenta nueva", async ({
  browser,
}) => {
  const admin = await person(browser, "Administración V18");
  grantRole(admin.user.email, "admin");
  const { page, user } = await person(browser, "Persona V18");
  await page.goto("/inicio");
  const userId = await myId(page);
  const api = await apiAs(await accessTokenFrom(page));

  // Solicitud con confirmación escrita (escenarios 7.1 y 7.2).
  await page.goto("/mi-cuenta");
  const section = page.getByRole("region", { name: "Eliminar mi cuenta" });
  await expect(section).toContainText("no se puede deshacer");
  await expectNoA11yViolations(page);
  await section.getByRole("button", { name: "Eliminar mi cuenta" }).click();
  const dialog = page.getByRole("alertdialog", { name: /eliminar tu cuenta/i });
  const confirm = dialog.getByRole("button", { name: "Eliminar definitivamente" });
  await expect(confirm).toBeDisabled();
  await dialog.getByRole("textbox", { name: /escribe ELIMINAR/i }).fill("ELIMINAR");
  await confirm.click();
  await expect(page.getByRole("status", { name: /solicitamos la supresión/i })).toContainText(
    /a más tardar el \d{1,2} de \p{L}+ de \d{4}/u,
  );

  // El acceso termina de inmediato: el token anterior ya no sirve y la app pide ingresar.
  expect((await api.get("/api/v1/me")).status()).toBe(401);
  await api.dispose();
  await page.goto("/inicio");
  await expect(page).toHaveURL(/\/ingresar(\?|$)/);

  // El administrador ve la solicitud con su fecha límite (escenario 7.4).
  await admin.page.goto("/admin/supresiones");
  const table = admin.page.getByRole("table", { name: "Solicitudes de supresión" });
  const row = table.getByRole("row").filter({ hasText: userId });
  await expect(row).toContainText("Solicitud de la persona");
  await expect(row).toContainText(/\d{1,2} de \p{L}+ de \d{4}/u);
  await expectNoA11yViolations(admin.page);

  // El worker la completa (SC-006) y la cuenta ya no aparece.
  await expect.poll(() => deletionRequestStatus(userId), { timeout: 60_000 }).toBe("completed");
  await admin.page.reload();
  await expect(table.getByRole("row").filter({ hasText: userId })).toContainText("Completada");
  const adminApi = await apiAs(await accessTokenFrom(admin.page));
  const search = (await (
    await adminApi.get("/api/v1/admin/users", { params: { q: user.email } })
  ).json()) as { total: number };
  expect(search.total).toBe(0);
  await adminApi.dispose();

  // Reingresar con la misma cuenta institucional crea una cuenta nueva (escenario 7.3).
  await signInWithMicrosoft(page, user);
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);
  const again = await apiAs(await accessTokenFrom(page));
  const me = (await (await again.get("/api/v1/me")).json()) as { id: string };
  await again.dispose();
  expect(me.id).not.toBe(userId);
});
