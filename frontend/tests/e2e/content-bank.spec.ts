/**
 * T121: lista del banco contra el stack e2e (fase 13; parte de interfaz de B1; FR-039, FR-043).
 */
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

test("B1 en la interfaz: el banco inicial en /banco, con búsqueda y filtros", async ({ page }) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente lista" });
  grantRole(user.email, "teacher");
  await page.goto("/banco");
  await expect(page.getByRole("heading", { level: 1, name: "Banco de ítems" })).toBeVisible();

  await page.getByRole("searchbox", { name: "Buscar" }).fill("LC-0007");
  await page.getByRole("button", { name: "Buscar" }).click();
  const table = page.getByRole("table", { name: "Ítems del banco" });
  const row = table.getByRole("row").filter({ has: page.getByRole("link", { name: "LC-0007" }) });
  await expect(row).toContainText("Lectura crítica");
  await expect(row).toContainText("IA");
  await expect(page).toHaveURL(/q=LC-0007/);

  await page.goto("/banco?module=ING");
  await expect(page.getByLabel("Módulo")).toHaveValue("ING");
  const modules = await table.getByRole("row").locator("td:nth-child(2)").allInnerTexts();
  expect(modules.length).toBeGreaterThan(0);
  expect(new Set(modules)).toEqual(new Set(["Inglés"]));
  await expectNoA11yViolations(page);
});

test("FR-043: filtra por señal de problema", async ({ page }) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente señales" });
  grantRole(user.email, "teacher");
  const code = newItemCode();
  cloneItem("LC-0001", code, { state: "published" });
  psqlExec(
    `INSERT INTO content.item_version_stats (version_id, first_responses, correct_rate, signals, computed_at)
     SELECT v.id, 40, 0.1, ARRAY['too_hard'], now() FROM content.item_versions v
     JOIN content.items i ON i.id = v.item_id WHERE i.code = :'code'
     ON CONFLICT (version_id) DO UPDATE SET signals = EXCLUDED.signals;`,
    { code },
  );

  await page.goto("/banco");
  await page.getByLabel("Señal de problema").selectOption("too_hard");
  await page.getByRole("searchbox", { name: "Buscar" }).fill(code);
  await page.getByRole("button", { name: "Buscar" }).click();

  const row = page
    .getByRole("table", { name: "Ítems del banco" })
    .getByRole("row")
    .filter({ has: page.getByRole("link", { name: code }) });
  await expect(row).toContainText("Muy difícil");
  await expect(page).toHaveURL(/signal=too_hard/);
});

test("FR-039: la cobertura enlaza al banco filtrado por la categoría", async ({ page }) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente cobertura lista" });
  grantRole(user.email, "teacher");
  await page.goto("/banco/cobertura");

  const link = page
    .getByRole("table", { name: "Cobertura de Lectura crítica" })
    .getByRole("link")
    .first();
  const href = (await link.getAttribute("href")) ?? "";
  const node = new URLSearchParams(href.split("?")[1]).get("taxonomy_node");
  await link.click();

  await expect(page).toHaveURL(/\/banco\?module=LC&taxonomy_node=/);
  await expect(page.getByLabel("Categoría")).toHaveValue(node ?? "");
  await expect(page.getByRole("heading", { level: 1, name: "Banco de ítems" })).toBeVisible();
});
