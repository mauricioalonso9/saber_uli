/**
 * T173: accesibilidad WCAG 2.2 AA en todas las rutas de research R-35, en viewport móvil (los
 * proyectos pixel-7 e iphone-14), con navegación por teclado y foco visible (constitución VII).
 */
import { type Page, expect, test } from "@playwright/test";

import { accessTokenFrom, apiAs } from "./fixtures/api";
import { newMockUser, signInWithMicrosoft } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { decide, onboardedUser } from "./fixtures/consent";
import { grantRole } from "./fixtures/db";

/** El ingreso con el proveedor simulado necesita resolver `oidc` (no aplica sin sesión). */
const needsOidc = (browserName: string) =>
  browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES;
const OIDC_HINT = "WebKit necesita `127.0.0.1 oidc` en el archivo hosts";

test.describe.configure({ timeout: 180_000 });

/** Las primeras paradas del tabulador (hasta tres) son visibles y muestran el foco (WCAG 2.4.7,
 * 2.4.11). */
async function expectKeyboardFocus(page: Page): Promise<void> {
  await page.locator("body").click({ position: { x: 1, y: 1 } });
  for (let stop = 0; stop < 3; stop += 1) {
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    // Una página con pocos controles devuelve el foco al navegador tras el último.
    if (stop > 0 && (await focused.count()) === 0) return;
    await expect(focused, `parada ${stop + 1} del tabulador`).toBeVisible();
    const indicator = await focused.evaluate((element) => {
      const style = getComputedStyle(element);
      const outline = style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0;
      const ring = style.boxShadow !== "none";
      const filled = style.backgroundColor !== "rgba(0, 0, 0, 0)";
      return outline || ring || filled;
    });
    expect(indicator, `foco visible en la parada ${stop + 1}`).toBe(true);
  }
}

async function check(page: Page, path: string, heading: string | RegExp): Promise<void> {
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await expectNoA11yViolations(page);
  await expectKeyboardFocus(page);
}

test("rutas sin sesión", async ({ page }) => {
  await check(page, "/ingresar", "Ingresar");
  await check(page, "/ingresar/invitado", "Ingresar como invitado");
  await check(page, "/acceso", "Acceso de invitado");
});

test("primer ingreso: autorización y perfil", async ({ page, browserName }) => {
  test.skip(needsOidc(browserName), OIDC_HINT);
  await signInWithMicrosoft(page, newMockUser());
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);
  await expectNoA11yViolations(page);
  await expectKeyboardFocus(page);
  await decide(page, "Acepto");
  await expect(page).toHaveURL(/\/bienvenida\/perfil$/);
  await expectNoA11yViolations(page);
  await expectKeyboardFocus(page);
});

test("rutas de la persona, del docente y del administrador", async ({
  page,
  browser,
  browserName,
}) => {
  test.skip(needsOidc(browserName), OIDC_HINT);
  // Datos para que las tablas y listas no estén vacías.
  const leaving = await (await browser.newContext()).newPage();
  await onboardedUser(leaving, { ...newMockUser(), name: "Persona A11y" });
  const leavingApi = await apiAs(await accessTokenFrom(leaving));
  expect(
    (
      await leavingApi.post("/api/v1/me/deletion-request", { data: { confirmation: "ELIMINAR" } })
    ).status(),
  ).toBe(202);
  await leavingApi.dispose();

  const user = await onboardedUser(page, { ...newMockUser(), name: "Administración A11y" });
  grantRole(user.email, "admin");
  grantRole(user.email, "teacher");
  await page.goto("/inicio");
  const api = await apiAs(await accessTokenFrom(page));
  const group = (await (
    await api.post("/api/v1/admin/groups", { data: { name: `Grupo A11y ${Date.now()}` } })
  ).json()) as { id: string };
  await api.dispose();

  const routes: [string, string | RegExp][] = [
    ["/inicio", "Inicio"],
    ["/mi-cuenta", "Mi cuenta"],
    ["/mi-cuenta/datos", "Mis datos"],
    ["/mi-cuenta/autorizacion", /autorización/i],
    ["/invitaciones", "Invitaciones"],
    ["/grupos", "Mis grupos"],
    ["/admin/usuarios", "Cuentas"],
    ["/admin/grupos", "Grupos"],
    [`/admin/grupos/${group.id}`, /Grupo A11y/],
    ["/admin/programas", "Programas"],
    ["/admin/supresiones", "Solicitudes de supresión"],
    ["/admin/politica", /política/i],
    ["/admin/parametros", "Parámetros"],
    ["/admin/auditoria", "Auditoría"],
  ];
  for (const [path, heading] of routes) {
    await test.step(path, () => check(page, path, heading));
  }
});
