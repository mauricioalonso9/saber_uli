/**
 * T069: prueba de humo contra el stack con perfil e2e. Sin sesión, `/` lleva al ingreso; la
 * página está en es-CO, es accesible (WCAG 2.2 AA) y la PWA publica su manifiesto.
 *
 * T174: Lighthouse 12 ya no tiene la categoría PWA, así que la instalabilidad se comprueba aquí con
 * el mismo criterio de Chrome (`Page.getInstallabilityErrors`).
 */
import { expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./fixtures/axe";

test("sin sesión, la raíz lleva a /ingresar en español y accesible", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/ingresar/);
  await expect(page.getByRole("heading", { name: "Ingresar" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "es-CO");
  await expect(page.getByRole("status", { name: "Estado de conexión" })).toHaveText("En línea");
  await expectNoA11yViolations(page);
});

test("la PWA publica su manifiesto en es-CO", async ({ request }) => {
  const response = await request.get("/manifest.webmanifest");

  expect(response.ok()).toBe(true);
  const manifest = (await response.json()) as { lang: string; name: string; display: string };
  expect(manifest).toMatchObject({ lang: "es-CO", name: "Saber Uli", display: "standalone" });
});

test("Chrome considera instalable la PWA", async ({ page, browserName }) => {
  test.skip(browserName !== "chromium", "solo Chromium expone los criterios de instalación");
  await page.goto("/ingresar");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });

  const cdp = await page.context().newCDPSession(page);
  const { installabilityErrors } = await cdp.send("Page.getInstallabilityErrors");

  expect(installabilityErrors).toEqual([]);
});

test("la API responde a través del proxy", async ({ request }) => {
  const response = await request.get("/api/health");

  expect(await response.json()).toEqual({ status: "ok" });
});
