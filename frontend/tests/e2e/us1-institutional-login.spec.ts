/**
 * T081: ingreso con la cuenta institucional contra el stack con perfil e2e (US1; FR-001 a
 * FR-005; escenarios 1.1 a 1.4). El proveedor es `mock-oauth2-server` en `http://oidc:8080`.
 */
import { expect, test } from "@playwright/test";

import { newMockUser, signInWithMicrosoft } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";

// WebKit no admite `--host-resolver-rules`: sin una entrada `oidc` en el archivo hosts del equipo
// (CI la agrega y define E2E_OIDC_RESOLVES=1) no puede alcanzar el proveedor simulado.
test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("un usuario del inquilino ingresa y llega a la autorización de datos", async ({ page }) => {
  await signInWithMicrosoft(page, newMockUser());

  await expect(page).toHaveURL(/\/bienvenida\/datos$/);
  await expect(page.getByRole("heading", { name: "Tratamiento de tus datos" })).toBeVisible();
});

test("una cuenta de otro inquilino ve el rechazo y no queda con sesión", async ({ page }) => {
  await signInWithMicrosoft(page, newMockUser({ external: true }));

  await expect(page).toHaveURL(/\/ingresar\?error=tenant_not_allowed/);
  await expect(page.getByRole("alert")).toContainText("no pertenece a la Universidad Libre");
  await expect(page.getByRole("alert")).toContainText("invitación");

  await page.goto("/inicio");
  await expect(page).toHaveURL(/\/ingresar/);
});

test("cerrar sesión exige ingresar de nuevo", async ({ page }) => {
  await signInWithMicrosoft(page, newMockUser());
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);

  await page.getByRole("button", { name: "Cerrar sesión" }).click();

  await expect(page).toHaveURL(/\/ingresar/);
  await page.goto("/bienvenida/datos");
  await expect(page).toHaveURL(/\/ingresar/);
});

test("/ingresar no tiene infracciones de accesibilidad AA", async ({ page }) => {
  await page.goto("/ingresar?error=tenant_not_allowed");
  await expect(page.getByRole("alert")).toBeVisible();

  await expectNoA11yViolations(page);
});
