/**
 * T187: cuenta local de administración (enmienda de 001, US9; FR-040 a FR-045).
 *
 * Usa la única cuenta `adminsaber`, así que corre en el proyecto serial `estado-global`. Antes y
 * después restablece la contraseña inicial con el comando del servidor, para dejar la cuenta como
 * la entrega la instalación.
 */
import { execFileSync } from "node:child_process";

import { type Page, expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./fixtures/axe";
import { composeContainer } from "./fixtures/db";

const NEW_PASSWORD = "una frase larga para la prueba e2e";

function resetLocalAdmin(): void {
  const container = process.env.E2E_API_CONTAINER ?? composeContainer("api");
  execFileSync("docker", ["exec", container, "saber-uli", "identity", "reset-local-password"], {
    stdio: ["ignore", "ignore", "inherit"],
  });
}

async function signIn(page: Page, password: string): Promise<void> {
  await page.goto("/ingresar");
  await page.getByRole("button", { name: "Ingreso de administración" }).click();
  await page.getByLabel("Usuario").fill("adminsaber");
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar con usuario y contraseña" }).click();
}

test.beforeAll(resetLocalAdmin);
test.afterAll(resetLocalAdmin);

test("adminsaber: contraseña inicial, cambio obligatorio y administración", async ({ page }) => {
  await signIn(page, "otra contraseña");
  await expect(
    page.getByRole("alert").filter({ hasText: "El usuario o la contraseña no son correctos." }),
  ).toBeVisible();

  await signIn(page, "adminsaber");
  await expect(page).toHaveURL(/\/cambiar-contrasena$/);
  await expect(page.getByRole("heading", { level: 1, name: "Cambia la contraseña" })).toBeVisible();
  await expectNoA11yViolations(page);

  // Nada más hasta cambiarla (FR-041).
  await page.goto("/admin/usuarios");
  await expect(page).toHaveURL(/\/cambiar-contrasena$/);

  await page.getByLabel("Contraseña actual", { exact: true }).fill("adminsaber");
  await page.getByLabel("Contraseña nueva", { exact: true }).fill("password1234");
  await page.getByLabel("Repite la contraseña nueva").fill("password1234");
  await page.getByRole("button", { name: "Cambiar la contraseña" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "demasiado común" })).toBeVisible();

  await page.getByLabel("Contraseña nueva", { exact: true }).fill(NEW_PASSWORD);
  await page.getByLabel("Repite la contraseña nueva").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Cambiar la contraseña" }).click();
  await expect(page).toHaveURL(/\/inicio$/);

  await page.goto("/admin/usuarios");
  await expect(page.getByRole("heading", { level: 1, name: "Cuentas" })).toBeVisible();

  // Con la contraseña nueva vuelve a entrar sin cambio pendiente; la inicial ya no sirve.
  await page.context().clearCookies();
  await signIn(page, "adminsaber");
  await expect(page.getByRole("alert")).toBeVisible();
  await signIn(page, NEW_PASSWORD);
  await expect(page).toHaveURL(/\/inicio$/);
});
