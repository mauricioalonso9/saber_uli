/**
 * T095: cobertura del banco contra el stack e2e (US7; quickstart B18; FR-039).
 */
import { expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { grantRole } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("B18: la cobertura de Inglés por parte, con los faltantes en texto", async ({ page }) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente cobertura" });
  grantRole(user.email, "teacher");
  await page.goto("/banco/cobertura");
  await expect(page.getByRole("heading", { name: "Cobertura del banco" })).toBeVisible();

  await page.getByLabel("Módulo").selectOption("ING");

  const table = page.getByRole("table", { name: "Cobertura de Inglés" });
  await expect(table.getByRole("row")).toHaveCount(8); // encabezado y 7 partes
  await expect(page.getByText(/Meta del banco: \d+ ítems/)).toBeVisible();
  const status = await table.getByRole("row").nth(1).getByRole("cell").last().innerText();
  expect(status).toMatch(/^(Falta \d+|Faltan \d+|Cumple el objetivo)$/);
  await expect(table.getByRole("link").first()).toHaveAttribute(
    "href",
    /^\/banco\?module=ING&taxonomy_node=/,
  );
  await expectNoA11yViolations(page);
});
