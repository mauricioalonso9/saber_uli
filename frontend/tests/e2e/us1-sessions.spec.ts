/**
 * T178b: ver y cerrar las sesiones abiertas (escenario 1.5; FR-037a; ASVS 3.3.4).
 *
 * Dos contextos de navegador son dos dispositivos de la misma persona. Desde el primero se cierra
 * la sesión del segundo, que en su siguiente petición vuelve al ingreso.
 */
import { expect, test } from "@playwright/test";

import { signInWithMicrosoft } from "./fixtures/auth";
import { onboardedUser } from "./fixtures/consent";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("escenario 1.5: desde Mi cuenta se cierra la sesión de otro dispositivo", async ({
  page,
  browser,
}) => {
  const user = await onboardedUser(page);
  const { baseURL, locale } = test.info().project.use;
  const other = await browser.newContext({ baseURL, locale });
  const phone = await other.newPage();
  await signInWithMicrosoft(phone, user);
  await expect(phone).toHaveURL(/\/inicio$/);

  await page.goto("/mi-cuenta");
  const section = page.getByRole("region", { name: "Sesiones abiertas" });
  await expect(section.getByRole("listitem")).toHaveCount(2);
  await expect(section.getByRole("listitem").filter({ hasText: "este dispositivo" })).toHaveCount(
    1,
  );

  await section.getByRole("button", { name: /Cerrar la sesión de/ }).click();
  await expect(section.getByRole("status")).toHaveText(/La sesión se cerró/);
  await expect(section.getByRole("listitem")).toHaveCount(1);

  // El otro dispositivo pierde el acceso en su siguiente petición.
  await phone.goto("/mi-cuenta");
  await expect(phone).toHaveURL(/\/ingresar/);
  await other.close();
});
