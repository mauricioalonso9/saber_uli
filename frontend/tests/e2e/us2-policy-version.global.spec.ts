/**
 * T093: nueva versión de la política (US2; quickstart V4; FR-017): al publicarla, todos deben
 * aceptarla en su siguiente navegación.
 *
 * Cambia la versión vigente para todos los usuarios, así que corre en el proyecto
 * `estado-global` de `playwright.config.ts`: después de las demás pruebas y sin paralelismo.
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { decide, onboardedUser } from "./fixtures/consent";
import { grantAdmin } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

const POLICY_BODY = [
  "## Finalidades",
  "",
  "Usamos sus datos para identificarle, medir su progreso y recomendarle práctica.",
  "",
  "## Sus derechos",
  "",
  "Puede conocer, actualizar, rectificar y suprimir sus datos, y revocar esta autorización.",
  "",
  "## Canales",
  "",
  "Escriba al correo de protección de datos de la Universidad Libre.",
].join("\n");

async function newPage(browser: Browser): Promise<Page> {
  const context = await browser.newContext();
  return context.newPage();
}

test("V4: una versión nueva de la política exige aceptarla a todos", async ({ browser }) => {
  const student = await newPage(browser);
  await onboardedUser(student);

  const adminPage = await newPage(browser);
  const admin = await onboardedUser(adminPage, { ...newMockUser(), name: "Administración" });
  grantAdmin(admin.email);

  // Cargar la página renueva el token: ahora con el rol Administrador y sesión privilegiada.
  await adminPage.goto("/admin/politica");
  await expect(
    adminPage.getByRole("heading", { name: "Política de tratamiento de datos" }),
  ).toBeVisible();
  const version = `1.${Date.now() % 100_000}`;
  await adminPage.getByLabel("Número de versión").fill(version);
  await adminPage.getByLabel("Título").fill(`Política de tratamiento de datos ${version}`);
  await adminPage.getByLabel("Texto de la política (Markdown)").fill(POLICY_BODY);
  await adminPage.getByRole("button", { name: "Vista previa" }).click();
  await expect(adminPage.getByRole("article")).toContainText("Sus derechos");
  await expectNoA11yViolations(adminPage);
  await adminPage.getByRole("button", { name: "Publicar versión" }).click();
  await expect(adminPage.getByText(`Publicaste la versión ${version}.`)).toBeVisible();

  // En su siguiente navegación, el estudiante debe aceptar la versión nueva.
  await student.goto("/inicio");
  await expect(student).toHaveURL(/\/bienvenida\/datos$/);
  await expect(student.getByText(`Versión ${version}, vigente desde`)).toBeVisible();
  await decide(student, "Acepto");
  await expect(student).toHaveURL(/\/inicio$/);

  // Quien publica también.
  await adminPage.goto("/inicio");
  await expect(adminPage).toHaveURL(/\/bienvenida\/datos$/);
});
