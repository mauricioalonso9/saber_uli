/**
 * T103: primer ingreso completo contra el stack con perfil e2e (US3; quickstart V1; FR-019 a
 * FR-022; SC-001): ingreso, autorización y perfil hasta `/inicio` en menos de 60 s; retomar el
 * primer ingreso en el paso pendiente; editar el perfil desde `/mi-cuenta`.
 */
import { type Page, expect, test } from "@playwright/test";

import { newMockUser, signInWithMicrosoft } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { decide } from "./fixtures/consent";
import { ensureProgram } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

const PROGRAM = { code: "E2E-DER", name: "Derecho E2E", campus: "Bogotá" };

test.beforeAll(() => {
  ensureProgram(PROGRAM.code, PROGRAM.name, PROGRAM.campus);
});

async function completeProfile(page: Page, semester = "8"): Promise<void> {
  await expect(page).toHaveURL(/\/bienvenida\/perfil$/);
  await page
    .getByRole("combobox", { name: "Programa académico" })
    .selectOption({ label: `${PROGRAM.name} (${PROGRAM.campus})` });
  await page.getByRole("combobox", { name: "Semestre" }).selectOption(semester);
  await page.getByLabel("Fecha estimada de tu prueba Saber Pro").fill("2027-05-30");
  await page.getByRole("radio", { name: "Intensa" }).check();
  await page.getByRole("button", { name: "Guardar y continuar" }).click();
}

test("V1: ingreso, autorización y perfil hasta el inicio en menos de 60 s (SC-001)", async ({
  page,
}) => {
  const started = Date.now();

  await signInWithMicrosoft(page, newMockUser());
  await decide(page, "Acepto");
  await expect(page.getByRole("heading", { name: "Completa tu perfil" })).toBeVisible();
  await expectNoA11yViolations(page);
  await completeProfile(page);

  await expect(page).toHaveURL(/\/inicio$/);
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  // El tiempo incluye el formulario del proveedor simulado y el análisis de accesibilidad.
  expect(Date.now() - started).toBeLessThan(60_000);
});

test("FR-022: al volver, el primer ingreso sigue en el paso pendiente", async ({ context }) => {
  const first = await context.newPage();
  await signInWithMicrosoft(first, newMockUser());
  await expect(first).toHaveURL(/\/bienvenida\/datos$/);
  await first.close();

  // Se cierra la app sin decidir: al abrirla de nuevo sigue en la autorización.
  const second = await context.newPage();
  await second.goto("/");
  await expect(second).toHaveURL(/\/bienvenida\/datos$/);
  await decide(second, "Acepto");
  await expect(second).toHaveURL(/\/bienvenida\/perfil$/);
  await second.close();

  // Con la autorización ya dada, retoma en el perfil.
  const third = await context.newPage();
  await third.goto("/inicio");
  await expect(third).toHaveURL(/\/bienvenida\/perfil$/);
  await completeProfile(third);
  await expect(third).toHaveURL(/\/inicio$/);
});

test("editar el perfil desde Mi cuenta (FR-021)", async ({ page }) => {
  const user = newMockUser();
  await signInWithMicrosoft(page, user);
  await decide(page, "Acepto");
  await completeProfile(page, "8");
  await expect(page).toHaveURL(/\/inicio$/);

  await page.getByRole("link", { name: "Mi cuenta" }).click();
  await expect(page.getByRole("heading", { name: "Mi cuenta" })).toBeVisible();
  await expect(page.getByText(user.email)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Semestre" })).toHaveValue("8");
  await expectNoA11yViolations(page);

  await page.getByRole("combobox", { name: "Semestre" }).selectOption("9");
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByText("Guardamos tus cambios.")).toBeVisible();

  await page.reload();
  await expect(page.getByRole("combobox", { name: "Semestre" })).toHaveValue("9");
});
