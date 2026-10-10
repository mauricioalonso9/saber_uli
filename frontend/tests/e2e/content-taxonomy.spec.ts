/**
 * T107: mantenimiento de la taxonomía contra el stack e2e (US9; quickstart B20; FR-045).
 */
import { randomBytes } from "node:crypto";

import { expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { cloneItem, newItemCode } from "./fixtures/content";
import { grantRole, psqlExec } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("B20: una evidencia en uso no se borra, se desactiva", async ({ page }) => {
  const admin = await onboardedUser(page, { ...newMockUser(), name: "Admin taxonomía" });
  grantRole(admin.email, "admin");
  const code = `LC-E${randomBytes(2).toString("hex").toUpperCase()}`;
  await page.goto("/admin/taxonomia");
  await expect(page.getByRole("heading", { name: "Taxonomía" })).toBeVisible();

  const form = page.getByRole("form", { name: "Agregar una categoría" });
  await form.getByLabel("Tipo de categoría").selectOption("evidence");
  const parent = form.getByLabel("Categoría padre");
  const value = await parent.locator("option", { hasText: /^LC-A1 · / }).getAttribute("value");
  await parent.selectOption(value ?? "");
  await form.getByLabel("Código de la categoría").fill(code);
  await form.getByLabel("Nombre de la categoría").fill("Evidencia de la prueba e2e");
  await form.getByRole("button", { name: "Agregar la categoría" }).click();
  await expect(page.getByRole("status").filter({ hasText: `Se agregó ${code}.` })).toBeVisible();

  // Un ítem empieza a usarla (preparado por SQL) mientras la página sigue abierta.
  const item = newItemCode();
  cloneItem("LC-0001", item);
  psqlExec(
    `UPDATE content.item_versions SET evidence_id =
       (SELECT id FROM content.taxonomy_nodes WHERE code = :'node')
     WHERE item_id = (SELECT id FROM content.items WHERE code = :'item');`,
    { node: code, item },
  );

  await page.getByRole("button", { name: `Borrar ${code}` }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "desactívala en lugar de borrarla" }),
  ).toBeVisible();

  await page.reload();
  await expect(page.getByRole("button", { name: `Borrar ${code}` })).toHaveCount(0);
  await page.getByRole("button", { name: `Desactivar ${code}` }).click();
  await expect(page.getByRole("status").filter({ hasText: `Se desactivó ${code}` })).toBeVisible();
  await expect(page.getByRole("listitem", { name: new RegExp(code) })).toContainText("Inactiva");
  await expectNoA11yViolations(page);

  // El ítem que la usa sigue abriendo con normalidad.
  await page.goto(`/banco/items/${item}`);
  await expect(page.getByRole("heading", { name: new RegExp(item) })).toBeVisible();
});

test("B20: un docente no ve la taxonomía", async ({ page }) => {
  const teacher = await onboardedUser(page, { ...newMockUser(), name: "Docente taxonomía" });
  grantRole(teacher.email, "teacher");

  await page.goto("/admin/taxonomia");

  await expect(page.getByRole("heading", { name: "Taxonomía" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Taxonomía" })).toHaveCount(0);
});
