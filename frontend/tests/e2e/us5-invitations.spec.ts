/**
 * T133: gestión de invitaciones contra el stack con perfil e2e (US5; quickstart V7 a V12;
 * FR-006 a FR-010; SC-003, SC-005).
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { accessTokenFrom, apiAs } from "./fixtures/api";
import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { decide, onboardedUser } from "./fixtures/consent";
import { grantRole, markGuestAccessExpired } from "./fixtures/db";
import { Mailpit } from "./fixtures/mailpit";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

// Varias personas ingresan y se esperan correos del worker: más que los 30 s por defecto.
test.describe.configure({ timeout: 90_000 });

let mailpit: Mailpit;

test.beforeAll(async () => {
  mailpit = await Mailpit.connect();
});

test.afterAll(async () => {
  await mailpit?.dispose();
});

const guestEmail = () => `invitado-${crypto.randomUUID().slice(0, 8)}@correo.co`;

/** Fecha `AAAA-MM-DD` dentro de `days` días (para los campos de fecha). */
function inDays(days: number): string {
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

/** Docente o administrador con sesión privilegiada en `/invitaciones`. */
async function staffPage(browser: Browser, role: "teacher" | "admin"): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  const user = await onboardedUser(page, { ...newMockUser(), name: `Personal ${role}` });
  grantRole(user.email, role);
  // Cargar la página renueva el token: ahora con el rol y sesión privilegiada.
  await page.goto("/invitaciones");
  await expect(page.getByRole("heading", { name: "Invitaciones", level: 1 })).toBeVisible();
  return page;
}

async function invite(page: Page, email: string, until?: string): Promise<void> {
  const form = page.getByRole("form", { name: "Invitar a una persona" });
  await form.getByRole("textbox", { name: "Correo" }).fill(email);
  if (until) await form.getByLabel(/acceso hasta/i).fill(until);
  await form.getByRole("button", { name: "Enviar invitación" }).click();
}

async function enterAsGuest(browser: Browser, email: string, subject: string): Promise<Page> {
  const message = await mailpit.latestFor(email, 60_000, subject);
  const page = await (await browser.newContext()).newPage();
  await page.goto(Mailpit.linkTo(message, "/acceso"));
  await page.getByRole("button", { name: "Ingresar" }).click();
  return page;
}

async function completeGuestOnboarding(page: Page): Promise<void> {
  await decide(page, "Acepto");
  await page.getByRole("textbox", { name: "Tu nombre" }).fill("Laura Gómez");
  await page.getByRole("button", { name: "Guardar y continuar" }).click();
  await expect(page).toHaveURL(/\/inicio$/);
}

function row(page: Page, email: string) {
  return page.getByRole("row", { name: new RegExp(email.replace(".", "\\.")) });
}

/** Busca la invitación por correo (con muchas invitaciones puede no estar entre las primeras). */
async function showRow(page: Page, email: string) {
  await page.getByRole("searchbox", { name: /buscar/i }).fill(email);
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(row(page, email)).toBeVisible();
  return row(page, email);
}

test("V7 y V8: correo institucional rechazado y plazo máximo del docente", async ({ browser }) => {
  const teacher = await staffPage(browser, "teacher");
  await expectNoA11yViolations(teacher);

  await invite(teacher, "alguien@unilibre.edu.co");
  await expect(teacher.getByRole("alert")).toContainText("cuenta Unilibre");

  await invite(teacher, guestEmail(), inDays(200));
  await expect(teacher.getByRole("alert")).toContainText("180 días");

  const admin = await staffPage(browser, "admin");
  await invite(admin, guestEmail(), inDays(200));
  await expect(admin.getByText(/enviamos la invitación/i)).toBeVisible();
});

test("V10: un docente solo ve sus invitaciones y las ajenas no se encuentran", async ({
  browser,
}) => {
  const teacherA = await staffPage(browser, "teacher");
  const teacherB = await staffPage(browser, "teacher");
  const email = guestEmail();
  await invite(teacherA, email);
  await expect(row(teacherA, email)).toBeVisible();

  await teacherB.reload();
  await expect(teacherB.getByRole("heading", { name: "Invitaciones", level: 1 })).toBeVisible();
  await expect(row(teacherB, email)).toHaveCount(0);

  const tokenA = await accessTokenFrom(teacherA);
  const asA = await apiAs(tokenA);
  const listed = await asA.get(`/api/v1/invitations?q=${encodeURIComponent(email)}`);
  const id = ((await listed.json()) as { items: { id: string }[] }).items[0]?.id;
  expect(id).toBeTruthy();
  const asB = await apiAs(await accessTokenFrom(teacherB));
  expect((await asB.get(`/api/v1/invitations/${id}`)).status()).toBe(404);
  await asA.dispose();
  await asB.dispose();
});

test("V11: la revocación termina la sesión del invitado en su siguiente acción (SC-003)", async ({
  browser,
}) => {
  const admin = await staffPage(browser, "admin");
  const email = guestEmail();
  await invite(admin, email);
  const guest = await enterAsGuest(browser, email, "Tu invitación a Saber Uli");
  await completeGuestOnboarding(guest);

  await admin.reload();
  await (await showRow(admin, email)).getByRole("button", { name: /revocar el acceso/i }).click();
  await admin.getByRole("button", { name: "Sí, revocar" }).click();
  await expect(admin.getByText(/revocamos el acceso/i)).toBeVisible();

  await guest.getByRole("link", { name: "Mi cuenta" }).click();
  await expect(guest).toHaveURL(/\/ingresar\?error=guest_access_revoked/);
  await expect(guest.getByRole("alert")).toContainText("fue retirado");
  await guest.goto("/inicio");
  await expect(guest).toHaveURL(/\/ingresar/);
});

test("V12: renovar un acceso vencido conserva el progreso del invitado", async ({ browser }) => {
  const admin = await staffPage(browser, "admin");
  const email = guestEmail();
  await invite(admin, email);
  const guest = await enterAsGuest(browser, email, "Tu invitación a Saber Uli");
  await completeGuestOnboarding(guest);

  markGuestAccessExpired(email);
  await admin.reload();
  await expect(await showRow(admin, email)).toContainText("Vencida");
  await row(admin, email)
    .getByRole("button", { name: /cambiar vencimiento/i })
    .click();
  await admin.getByLabel("Nuevo vencimiento").fill(inDays(30));
  await admin.getByRole("button", { name: "Guardar" }).click();
  await expect(admin.getByText(/actualizamos el vencimiento/i)).toBeVisible();
  await expect(row(admin, email)).toContainText("Aceptada");

  // El invitado pide un enlace y vuelve directo al inicio: su perfil se conservó.
  // Desde otro dispositivo (sin sesión), el invitado pide un enlace de ingreso.
  const requester = await (await browser.newContext()).newPage();
  await requester.goto("/ingresar/invitado");
  await requester.getByRole("textbox", { name: "Tu correo" }).fill(email);
  await requester.getByRole("button", { name: "Enviarme un enlace" }).click();
  await expect(requester.getByText(/si el correo corresponde/i)).toBeVisible();
  const back = await enterAsGuest(browser, email, "Tu enlace para ingresar a Saber Uli");
  await expect(back).toHaveURL(/\/inicio$/);
});
