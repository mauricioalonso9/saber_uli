/**
 * T150: roles y grupos contra el stack con perfil e2e (US6; quickstart V13 a V15; FR-023 a
 * FR-030; R-15). El último administrador está en `us6-last-admin.global.spec.ts`.
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { accessTokenFrom, apiAs } from "./fixtures/api";
import { type MockUser, newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { ensureProgram, grantRole, idlePrivilegedSession } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test.describe.configure({ timeout: 90_000 });

const PROGRAM = { code: "E2E-DER", name: "Derecho E2E", campus: "Bogotá" };

test.beforeAll(() => {
  ensureProgram(PROGRAM.code, PROGRAM.name, PROGRAM.campus);
});

interface Person {
  page: Page;
  user: MockUser;
}

async function person(browser: Browser, name: string, role?: "admin" | "teacher"): Promise<Person> {
  const page = await (await browser.newContext()).newPage();
  const user = await onboardedUser(page, { ...newMockUser(), name });
  if (role) grantRole(user.email, role);
  await page.goto("/inicio");
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  return { page, user };
}

async function findAccount(admin: Page, email: string): Promise<void> {
  await admin.goto("/admin/usuarios");
  await admin.getByRole("searchbox", { name: /buscar/i }).fill(email);
  await admin.getByRole("button", { name: "Buscar" }).click();
  await expect(admin.getByRole("table", { name: "Cuentas" })).toContainText(email);
}

test("V13: roles combinados con la unión de sus permisos", async ({ browser }) => {
  const admin = await person(browser, "Administración V13", "admin");
  const target = await person(browser, "Persona V13");

  await findAccount(admin.page, target.user.email);
  await expectNoA11yViolations(admin.page);
  await admin.page.getByRole("button", { name: `Editar roles de ${target.user.name}` }).click();
  const editor = admin.page.getByRole("group", { name: `Roles de ${target.user.name}` });
  await editor.getByRole("checkbox", { name: "Docente" }).check();
  await editor.getByRole("checkbox", { name: "Director de programa" }).check();
  await editor.getByRole("checkbox", { name: `${PROGRAM.name} (${PROGRAM.campus})` }).check();
  await editor.getByRole("button", { name: "Guardar roles" }).click();
  await expect(admin.page.getByText(/actualizamos los roles/i)).toBeVisible();

  // Con sus nuevos roles (al renovar la sesión) ve las funciones de Docente.
  await target.page.reload();
  const nav = target.page.getByRole("navigation", { name: "Principal" });
  await expect(nav.getByRole("link", { name: "Invitaciones" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Mis grupos" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Cuentas" })).toHaveCount(0);
});

test("V14: el docente ve nombres sin correos y el director no ve datos identificables", async ({
  browser,
}) => {
  const admin = await person(browser, "Administración V14", "admin");
  const teacher = await person(browser, "Docente V14", "teacher");
  const student = await person(browser, "Ana Estudiante V14");
  const director = await person(browser, "Director V14");

  // Grupo con el estudiante y el docente.
  await admin.page.goto("/admin/grupos");
  const groupName = `Grupo V14 ${crypto.randomUUID().slice(0, 6)}`;
  const form = admin.page.getByRole("form", { name: "Crear un grupo" });
  await form.getByRole("textbox", { name: "Nombre" }).fill(groupName);
  await form.getByRole("button", { name: "Crear grupo" }).click();
  await admin.page.getByRole("link", { name: `Gestionar ${groupName}` }).click();
  const students = admin.page.getByRole("region", { name: "Estudiantes" });
  await students.getByRole("searchbox").fill(student.user.email);
  await students.getByRole("button", { name: "Buscar" }).click();
  await students.getByRole("button", { name: `Agregar a ${student.user.name}` }).click();
  await expect(students).toContainText(student.user.email);
  const teachers = admin.page.getByRole("region", { name: "Docentes" });
  await teachers.getByRole("searchbox").fill(teacher.user.email);
  await teachers.getByRole("button", { name: "Buscar" }).click();
  await teachers.getByRole("button", { name: `Agregar a ${teacher.user.name}` }).click();
  await expect(teachers).toContainText(teacher.user.name);
  await expectNoA11yViolations(admin.page);

  // Director de programa sin rol Docente.
  await findAccount(admin.page, director.user.email);
  await admin.page.getByRole("button", { name: `Editar roles de ${director.user.name}` }).click();
  const editor = admin.page.getByRole("group", { name: `Roles de ${director.user.name}` });
  await editor.getByRole("checkbox", { name: "Director de programa" }).check();
  await editor.getByRole("checkbox", { name: `${PROGRAM.name} (${PROGRAM.campus})` }).check();
  await editor.getByRole("button", { name: "Guardar roles" }).click();
  await expect(admin.page.getByText(/actualizamos los roles/i)).toBeVisible();

  // El docente ve su grupo con el nombre del estudiante y ningún correo.
  await teacher.page.goto("/grupos");
  await teacher.page.getByRole("button", { name: new RegExp(groupName) }).click();
  const list = teacher.page.getByRole("list", { name: `Estudiantes de ${groupName}` });
  await expect(list).toContainText(student.user.name);
  expect(await teacher.page.locator("main").textContent()).not.toContain("@");
  await expectNoA11yViolations(teacher.page);

  // El director no llega a vistas con nombres ni correos.
  await director.page.reload();
  await director.page.goto("/grupos");
  await expect(director.page).toHaveURL(/\/inicio$/);
  const api = await apiAs(await accessTokenFrom(director.page));
  for (const path of ["/api/v1/teacher/groups", "/api/v1/admin/users", "/api/v1/invitations"]) {
    expect((await api.get(path)).status(), path).toBe(403);
  }
  await api.dispose();
});

test("V15: tras 31 minutos sin actividad privilegiada se pide autenticarse de nuevo", async ({
  browser,
}) => {
  const admin = await person(browser, "Administración V15", "admin");
  await admin.page.goto("/admin/usuarios");
  await expect(admin.page.getByRole("table", { name: "Cuentas" })).toBeVisible();

  idlePrivilegedSession(admin.user.email);
  await admin.page.reload();

  await expect(admin.page.getByRole("alert")).toContainText(/confirma tu identidad/i);
  await expect(admin.page.getByRole("button", { name: "Confirmar mi identidad" })).toBeVisible();
  // La práctica personal sigue sin interrupción.
  await admin.page.goto("/mi-cuenta");
  await expect(admin.page.getByRole("heading", { name: "Mi cuenta", exact: true })).toBeVisible();
  await expect(admin.page.getByRole("combobox", { name: "Semestre" })).toBeVisible();
});
