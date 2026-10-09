/**
 * T093: autorización de tratamiento de datos contra el stack con perfil e2e (US2; quickstart V3;
 * FR-014 a FR-018): "No acepto" bloquea todo salvo la política, el cierre de sesión y la
 * supresión; aceptar da acceso; revocar cierra la sesión en la siguiente acción.
 *
 * V4 (versión nueva) está en `us2-policy-version.global.spec.ts`: cambia la versión vigente para
 * todos y corre aparte, después de estas pruebas.
 */
import { expect, test } from "@playwright/test";

import { newMockUser, signInWithMicrosoft } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { decide, onboardedUser } from "./fixtures/consent";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test("V3: no aceptar bloquea todo salvo la política, el cierre de sesión y la supresión", async ({
  page,
}) => {
  await signInWithMicrosoft(page, newMockUser());
  await expect(page.getByRole("article")).toContainText("Finalidades");
  await expectNoA11yViolations(page);

  await decide(page, "No acepto");

  const explanation = page.getByRole("region", { name: "No aceptaste la política" });
  await expect(explanation).toContainText("no puedes usar ninguna función");
  await page.goto("/inicio");
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);
  await page.goto("/mi-cuenta/autorizacion");
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);

  // La supresión sigue disponible (FR-014).
  await page.goto("/mi-cuenta/datos");
  await expect(page).toHaveURL(/\/mi-cuenta\/datos$/);
  await expect(page.getByRole("heading", { name: "Mis datos" })).toBeVisible();

  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/ingresar/);
});

test("V3: aceptar da acceso y revocar cierra la sesión en la siguiente acción", async ({
  page,
}) => {
  const user = await onboardedUser(page);

  await page.goto("/mi-cuenta/autorizacion");
  const current = page.getByRole("region", { name: "Autorización vigente" });
  await expect(current).toContainText("Aceptaste la versión");
  await expectNoA11yViolations(page);

  await page.getByRole("button", { name: "Revocar mi autorización" }).click();
  await page.getByRole("button", { name: "Sí, revocar" }).click();
  await expect(page.getByRole("heading", { name: "Revocaste tu autorización" })).toBeVisible();

  // La sesión quedó revocada en el servidor: la cookie de renovación ya no sirve.
  const refresh = await page.request.post("/api/auth/refresh", {
    headers: { "X-Requested-With": "saber-uli" },
  });
  expect(refresh.status()).toBe(401);
  await page.getByRole("button", { name: "Ingresar de nuevo" }).click();
  await expect(page).toHaveURL(/\/ingresar/);

  // Al volver a ingresar debe autorizar de nuevo.
  await signInWithMicrosoft(page, user);
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);
});
