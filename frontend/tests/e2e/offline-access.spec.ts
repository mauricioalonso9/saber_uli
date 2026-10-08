/**
 * T172: uso sin conexión de la app instalada (quickstart V16; FR-038, FR-039; research R-17).
 *
 * - Sin conexión la app sigue funcionando hasta 7 días después de la última validación (reloj de
 *   Playwright con `setFixedTime`, que no detiene los temporizadores).
 * - El día 8 pide reconectarse.
 * - Al reconectar con el acceso retirado no se recupera la sesión, se explica la causa y la app
 *   deja de funcionar sin conexión.
 */
import { expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { onboardedUser } from "./fixtures/consent";
import { disableAccount } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

const DAY = 24 * 60 * 60 * 1000;

test("V16: sin conexión hasta el día 7, el día 8 pide reconectarse y la revocación se explica", async ({
  page,
  context,
}) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Persona V16" });
  // La app queda controlada por el service worker (instalada) y valida el acceso en línea.
  await page.goto("/inicio");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  const validatedAt = Date.now();

  // Modo avión, casi 7 días después: la app sigue funcionando con la instantánea guardada.
  await context.setOffline(true);
  await page.clock.setFixedTime(validatedAt + 7 * DAY - 60_000);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  await expect(page.getByRole("status", { name: "Estado de conexión" })).toHaveText("Sin conexión");
  await page.getByRole("link", { name: "Mi cuenta" }).click();
  await expect(page).toHaveURL(/\/mi-cuenta$/);

  // Día 8: pide reconectarse.
  await page.clock.setFixedTime(validatedAt + 8 * DAY);
  await page.reload();
  await expect(page).toHaveURL(/\/sin-conexion$/);
  await expect(page.getByText(/más de 7 días sin validar tu acceso/i)).toBeVisible();

  // Mientras tanto le retiraron el acceso: al reconectar se explica y no vuelve a entrar.
  disableAccount(user.email);
  await page.clock.setFixedTime(Date.now());
  await context.setOffline(false);
  await page.goto("/inicio");
  await expect(page).toHaveURL(/\/ingresar/);
  await expect(page.getByRole("alert")).toContainText(/desactivada/i);

  // Ya no hay instantánea: sin conexión tampoco entra.
  await context.setOffline(true);
  await page.goto("/inicio");
  await expect(page.getByRole("heading", { name: "Inicio" })).toHaveCount(0);
});
