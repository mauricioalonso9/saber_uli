/**
 * T102: estadísticas de un ítem contra el stack e2e (US8; quickstart B19; FR-041, FR-042).
 * En 002 la fuente de respuestas es nula: toda versión publicada aparece sin datos suficientes.
 */
import { expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { cloneItem, newItemCode } from "./fixtures/content";
import { grantRole } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("B19: una versión publicada sin respuestas dice que aún no hay datos", async ({ page }) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente estadísticas" });
  grantRole(user.email, "teacher");
  const code = newItemCode();
  cloneItem("LC-0001", code, { state: "published" });

  await page.goto(`/banco/items/${code}`);

  const statistics = page.getByRole("region", { name: "Estadísticas" });
  await expect(statistics.getByRole("heading", { name: "Versión 1 · Publicado" })).toBeVisible();
  await expect(statistics).toContainText(
    "Aún no hay datos suficientes: 0 respuestas (se necesitan al menos 30).",
  );
  await expectNoA11yViolations(page);
});
