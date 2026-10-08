/**
 * T150: el último administrador (quickstart V13; FR-025). Deja a una sola persona como
 * administradora, así que corre en el proyecto `estado-global`, después de las demás pruebas.
 */
import { expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { onboardedUser } from "./fixtures/consent";
import { grantRole, keepOnlyAdmin } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("V13: no se puede quitar el rol al único administrador activo", async ({ page }) => {
  const admin = await onboardedUser(page, { ...newMockUser(), name: "Única Administración" });
  grantRole(admin.email, "admin");
  keepOnlyAdmin(admin.email);

  await page.goto("/admin/usuarios");
  await page.getByRole("searchbox", { name: /buscar/i }).fill(admin.email);
  await page.getByRole("button", { name: "Buscar" }).click();
  await page.getByRole("button", { name: `Editar roles de ${admin.name}` }).click();
  const editor = page.getByRole("group", { name: `Roles de ${admin.name}` });
  await editor.getByRole("checkbox", { name: "Administrador" }).uncheck();
  await editor.getByRole("button", { name: "Guardar roles" }).click();

  await expect(page.getByRole("alert")).toContainText("último administrador activo");

  await page.getByRole("button", { name: `Desactivar a ${admin.name}` }).click();
  await page.getByRole("button", { name: "Sí, desactivar" }).click();
  await expect(page.getByRole("alert")).toContainText("último administrador activo");
});
