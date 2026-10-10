/**
 * T047: revisión y publicación del banco contra el stack e2e (US2; quickstart B5 a B8; FR-012 a
 * FR-014). Dos administradores y un docente; los ítems son copias propias de la prueba.
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { type MockUser, newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { cloneItemInReview, newItemCode } from "./fixtures/content";
import { grantRole } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test.describe.configure({ timeout: 120_000 });

interface Person {
  page: Page;
  user: MockUser;
}

async function person(browser: Browser, name: string, role: "admin" | "teacher"): Promise<Person> {
  const page = await (await browser.newContext()).newPage();
  const user = await onboardedUser(page, { ...newMockUser(), name });
  grantRole(user.email, role);
  await page.goto("/inicio");
  await expect(page.getByRole("heading", { name: "Inicio" })).toBeVisible();
  return { page, user };
}

test("B5–B8: aprobar, autoaprobación, docente que comenta, devolver y rechazar", async ({
  browser,
}) => {
  const first = await person(browser, "Administración B5", "admin");
  const second = await person(browser, "Administración B6", "admin");
  const teacher = await person(browser, "Docente B7", "teacher");
  const approve = newItemCode();
  const own = newItemCode();
  const toReturn = newItemCode();
  const toReject = newItemCode();
  cloneItemInReview("LC-0001", approve, teacher.user.email);
  cloneItemInReview("LC-0002", own, first.user.email);
  cloneItemInReview("LC-0003", toReturn, teacher.user.email);
  cloneItemInReview("LC-0004", toReject, teacher.user.email);

  // B5: la cola muestra el ítem; el administrador lo aprueba con las dos confirmaciones.
  await first.page.goto("/banco/revision");
  const queue = first.page.getByRole("table", { name: "Ítems por revisar" });
  await expect(queue.getByRole("link", { name: approve })).toBeVisible();
  await expect(queue.getByRole("link", { name: own })).toHaveCount(0);
  await expectNoA11yViolations(first.page);
  await queue.getByRole("link", { name: approve }).click();
  await first.page.getByRole("button", { name: "Aprobar" }).click();
  await first.page.getByRole("checkbox", { name: /alineado con la guía del ICFES/ }).check();
  await first.page.getByRole("checkbox", { name: /no reproduce preguntas del ICFES/ }).check();
  await first.page.getByRole("button", { name: "Publicar" }).click();
  await expect(
    first.page.getByRole("status").filter({ hasText: "El ítem quedó publicado." }),
  ).toBeVisible();
  await expect(first.page.getByRole("region", { name: "Versión publicada" })).toBeVisible();

  // B6: nadie aprueba lo que creó; el otro administrador sí puede.
  await first.page.goto(`/banco/items/${own}`);
  await expect(
    first.page.getByText("Modificaste esta versión: la debe aprobar otro administrador."),
  ).toBeVisible();
  await expect(first.page.getByRole("button", { name: "Aprobar" })).toHaveCount(0);
  await second.page.goto(`/banco/items/${own}`);
  await expect(second.page.getByRole("button", { name: "Aprobar" })).toBeVisible();

  // B7: el docente no revisa, pero comenta.
  await teacher.page.goto(`/banco/items/${toReturn}`);
  await expect(teacher.page.getByRole("button", { name: "Aprobar" })).toHaveCount(0);
  await teacher.page.getByRole("button", { name: "Comentar" }).click();
  await teacher.page.getByLabel("Comentario").fill("¿La opción B es ambigua?");
  await teacher.page.getByRole("button", { name: "Publicar comentario" }).click();
  await expect(
    teacher.page.getByRole("status").filter({ hasText: "Comentario publicado." }),
  ).toBeVisible();

  // B8: devolver con comentario y rechazar con motivo.
  await second.page.goto(`/banco/items/${toReturn}`);
  await second.page.getByRole("button", { name: "Devolver" }).click();
  await second.page.getByLabel("Comentario para el autor").fill("Revisa la opción C.");
  await second.page.getByRole("button", { name: "Devolver al autor" }).click();
  await expect(
    second.page.getByRole("status").filter({ hasText: "El ítem volvió a Borrador." }),
  ).toBeVisible();
  await teacher.page.goto(`/banco/items/${toReturn}`);
  await expect(
    teacher.page.getByText("Comentario de la revisión: Revisa la opción C."),
  ).toBeVisible();
  await expect(
    teacher.page.getByRole("list", { name: "Eventos" }).getByText("Revisa la opción C."),
  ).toBeVisible();

  await second.page.goto(`/banco/items/${toReject}`);
  await second.page.getByRole("button", { name: "Rechazar" }).click();
  await second.page.getByLabel("Motivo").fill("Reproduce una pregunta del ICFES.");
  await second.page.getByRole("button", { name: "Rechazar el ítem" }).click();
  await expect(
    second.page.getByRole("status").filter({ hasText: "El ítem quedó rechazado." }),
  ).toBeVisible();
});
