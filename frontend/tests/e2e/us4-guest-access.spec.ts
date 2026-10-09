/**
 * T120: acceso de invitados contra el stack con perfil e2e (US4; quickstart V5 y V6; FR-007,
 * FR-011, FR-013; SC-007).
 *
 * La invitación se crea con el comando de operación; el worker envía el correo a Mailpit.
 */
import { type Page, expect, test } from "@playwright/test";

import { expectNoA11yViolations } from "./fixtures/axe";
import { inviteGuest } from "./fixtures/cli";
import { decide } from "./fixtures/consent";
import { expireGuestAccess } from "./fixtures/db";
import { Mailpit } from "./fixtures/mailpit";

const INVITATION_SUBJECT = "Tu invitación a Saber Uli";
const SIGN_IN_SUBJECT = "Tu enlace para ingresar a Saber Uli";

let mailpit: Mailpit;

test.beforeAll(async () => {
  mailpit = await Mailpit.connect();
});

test.afterAll(async () => {
  await mailpit.dispose();
});

function newGuestEmail(): string {
  return `invitado-${crypto.randomUUID().slice(0, 8)}@correo.co`;
}

async function linkFrom(to: string, subject: string): Promise<string> {
  const message = await mailpit.latestFor(to, 60_000, subject);
  return Mailpit.linkTo(message, "/acceso");
}

async function enterWith(page: Page, link: string): Promise<void> {
  await page.goto(link);
  await expect(page.getByRole("heading", { name: "Acceso de invitado" })).toBeVisible();
  // El token no queda en la barra de direcciones ni en el historial.
  await expect(page).toHaveURL(/\/acceso$/);
  await page.getByRole("button", { name: "Ingresar" }).click();
}

async function completeGuestOnboarding(page: Page): Promise<void> {
  await decide(page, "Acepto");
  await expect(page).toHaveURL(/\/bienvenida\/perfil$/);
  await page.getByRole("textbox", { name: "Tu nombre" }).fill("Laura Gómez");
  await page.getByRole("radio", { name: "Casual" }).check();
  await page.getByRole("button", { name: "Guardar y continuar" }).click();
  await expect(page).toHaveURL(/\/inicio$/);
}

test("V5: invitación por correo, ingreso sin contraseña en menos de 2 minutos (SC-007)", async ({
  page,
}) => {
  const email = newGuestEmail();
  const started = Date.now();

  inviteGuest(email);
  const link = await linkFrom(email, INVITATION_SUBJECT);
  await enterWith(page, link);
  await expect(page.getByRole("heading", { name: "Tratamiento de tus datos" })).toBeVisible();
  await completeGuestOnboarding(page);

  // Incluye el envío del correo por el worker (el despachador corre cada 5 s).
  expect(Date.now() - started).toBeLessThan(120_000);
  await expect(page.getByRole("banner")).toBeVisible();

  // Un invitado no ve funciones de docentes ni de administración.
  await page.goto("/invitaciones");
  await expect(page).toHaveURL(/\/inicio$/);
  await page.goto("/admin/politica");
  await expect(page).toHaveURL(/\/inicio$/);

  // El enlace de la invitación ya no sirve.
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/ingresar/);
  await enterWith(page, link);
  await expect(page.getByRole("alert")).toContainText("no es válido, ya se usó o venció");
});

test("V5: pedir un enlace nuevo por correo y entrar con él", async ({ page }) => {
  const email = newGuestEmail();
  inviteGuest(email);
  await enterWith(page, await linkFrom(email, INVITATION_SUBJECT));
  await completeGuestOnboarding(page);
  await page.getByRole("button", { name: "Cerrar sesión" }).click();

  await page.goto("/ingresar");
  await page.getByRole("link", { name: /soy invitado/i }).click();
  await expect(page).toHaveURL(/\/ingresar\/invitado$/);
  await expectNoA11yViolations(page);
  await page.getByRole("textbox", { name: "Tu correo" }).fill(email);
  await page.getByRole("button", { name: "Enviarme un enlace" }).click();
  await expect(page.getByText(/si el correo corresponde/i)).toBeVisible();

  await enterWith(page, await linkFrom(email, SIGN_IN_SUBJECT));
  await expect(page).toHaveURL(/\/inicio$/);
  await expectNoA11yViolations(page);
});

test("V6: con el acceso vencido el invitado no entra", async ({ page }) => {
  const email = newGuestEmail();
  inviteGuest(email);
  const link = await linkFrom(email, INVITATION_SUBJECT);

  expireGuestAccess(email);
  await enterWith(page, link);

  await expect(page.getByRole("alert")).toContainText("venció");
  await page.goto("/inicio");
  await expect(page).toHaveURL(/\/ingresar/);
});
