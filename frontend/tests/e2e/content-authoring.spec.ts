/**
 * T063: autoría del banco contra el stack e2e (US3; quickstart B9 a B13; FR-015, FR-020,
 * FR-024 a FR-027). Los ítems y contextos son copias propias de la prueba.
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { type MockUser, newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { cloneContext, cloneItem, newContextCode, newItemCode } from "./fixtures/content";
import { grantRole } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test.describe.configure({ timeout: 180_000 });

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

function status(page: Page, text: string | RegExp) {
  return page.getByRole("status").filter({ hasText: text });
}

test("B9: editar lo publicado crea una versión nueva que se publica al aprobarla", async ({
  browser,
}) => {
  const teacher = await person(browser, "Docente B9", "teacher");
  const admin = await person(browser, "Administración B9", "admin");
  const code = newItemCode();
  cloneItem("LC-0001", code, { state: "published" });

  await teacher.page.goto(`/banco/items/${code}`);
  await expect(
    teacher.page.getByText(/Este ítem está publicado: al guardar se creará la versión 2/),
  ).toBeVisible();
  await teacher.page.getByLabel("Enunciado").fill(`Enunciado corregido (${code})`);
  await teacher.page.getByRole("button", { name: "Enviar a revisión" }).click();
  await expect(status(teacher.page, "El ítem quedó en revisión.")).toBeVisible();
  await teacher.page.reload();
  await expect(
    teacher.page
      .getByRole("region", { name: "Versión publicada" })
      .getByRole("heading", { level: 2 }),
  ).toContainText("versión 1");

  await admin.page.goto(`/banco/items/${code}`);
  await admin.page.getByRole("button", { name: "Aprobar" }).click();
  await admin.page.getByRole("checkbox", { name: /alineado con la guía del ICFES/ }).check();
  await admin.page.getByRole("checkbox", { name: /no reproduce preguntas del ICFES/ }).check();
  await admin.page.getByRole("button", { name: "Publicar" }).click();
  await expect(status(admin.page, "El ítem quedó publicado.")).toBeVisible();
  await expect(
    admin.page
      .getByRole("region", { name: "Versión publicada" })
      .getByRole("heading", { level: 2 }),
  ).toContainText("versión 2");
});

test("B10: el editor no deja enviar ni guardar contenido inválido", async ({ browser }) => {
  const teacher = await person(browser, "Docente B10", "teacher");
  const page = teacher.page;

  // Ítem de LC sin retroalimentación en una opción.
  await page.goto("/banco/items/nuevo");
  await page.getByLabel("Módulo").selectOption("LC");
  await page.getByLabel("Código", { exact: true }).fill(newItemCode());
  await page.getByLabel("Enunciado").fill("¿Cuál es la tesis del autor?");
  for (const key of "ABCD") {
    await page.getByLabel(`Texto de la opción ${key}`).fill(`Opción ${key}`);
    if (key !== "B") {
      await page.getByLabel(`Retroalimentación de la opción ${key}`).fill(`Por ${key}`);
    }
  }
  await page.getByRole("button", { name: "Enviar a revisión" }).click();
  await expect(page.getByLabel("Retroalimentación de la opción B")).toHaveAccessibleDescription(
    "La opción B necesita su retroalimentación.",
  );
  await expectNoA11yViolations(page);

  // Texto de 501 palabras en un contexto de LC.
  await page.goto("/banco/contextos/nuevo");
  await page.getByLabel("Módulo").selectOption("LC");
  await page.getByLabel("Código", { exact: true }).fill(newContextCode());
  await page.getByLabel("Título").fill("Texto largo");
  await page.getByLabel("Texto", { exact: true }).fill(Array(501).fill("palabra").join(" "));
  await expect(page.getByText("501/500 palabras")).toBeVisible();
  await page.getByRole("button", { name: "Crear contexto" }).click();
  await expect(page.getByLabel("Texto", { exact: true })).toHaveAccessibleDescription(
    /El texto tiene 501\/500 palabras/,
  );

  // Imagen sin texto alternativo.
  await page.getByLabel("Tipo de contexto").selectOption("image");
  await page.getByRole("button", { name: "Crear contexto" }).click();
  await expect(page.getByLabel("Texto alternativo")).toHaveAccessibleDescription(
    "Describe la imagen para quienes usan lector de pantalla.",
  );
  await expect(status(page, "Contexto creado.")).toHaveCount(0);
});

test("B11: vista previa móvil con contexto y retroalimentación", async ({ browser }) => {
  const teacher = await person(browser, "Docente B11", "teacher");
  const page = teacher.page;
  const matching = newItemCode();
  const table = newItemCode();
  cloneItem("ING-0001", matching);
  cloneItem("LC-0007", table);

  for (const code of [matching, table]) {
    await page.goto(`/banco/items/${code}`);
    const frame = page.getByRole("region", { name: "Vista en un celular de 360 × 800" }).first();
    await expect(frame).toBeVisible();
    await expect(frame).toContainText(code);
    const box = await frame.boundingBox();
    expect(Math.round(box?.width ?? 0)).toBe(360);
    await page.getByRole("tab", { name: "Retroalimentación" }).first().click();
    await expectNoA11yViolations(page);
  }
});

test("B12: editar un contexto compartido avisa y versiona lo publicado", async ({ browser }) => {
  const teacher = await person(browser, "Docente B12", "teacher");
  const page = teacher.page;
  const context = newContextCode();
  const item = newItemCode();
  cloneContext("ING-CTX-P1-001", context);
  cloneItem("ING-0001", item, { state: "published", contextCode: context });

  await page.goto(`/banco/contextos/${context}`);
  await page.getByLabel("Título").fill(`Avisos corregidos (${context})`);
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  const confirm = page.getByRole("alertdialog", { name: "¿Guardar el cambio del contexto?" });
  await expect(confirm).toContainText(
    "Este contexto lo usa 1 ítem; 1 está publicado y recibirá una versión nueva En revisión.",
  );
  await confirm.getByRole("button", { name: "Confirmar" }).click();
  await expect(status(page, `Pasaron a revisión: ${item}.`)).toBeVisible();

  await page.goto(`/banco/items/${item}`);
  await expect(page.getByRole("region", { name: "Versión publicada" })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /Mantener en revisión/ })).toBeVisible();
});

test("B13: la edición simultánea no pierde cambios", async ({ browser }) => {
  const first = await person(browser, "Docente B13 uno", "teacher");
  const second = await person(browser, "Docente B13 dos", "teacher");
  const code = newItemCode();
  cloneItem("LC-0005", code);

  await first.page.goto(`/banco/items/${code}`);
  await second.page.goto(`/banco/items/${code}`);
  await first.page.getByLabel("Enunciado").fill(`Primera persona (${code})`);
  await second.page.getByLabel("Enunciado").fill(`Segunda persona (${code})`);

  await first.page.getByRole("button", { name: "Guardar borrador" }).click();
  await expect(status(first.page, "Cambios guardados.")).toBeVisible();
  await second.page.getByRole("button", { name: "Guardar borrador" }).click();

  const dialog = second.page.getByRole("dialog", { name: "Otra persona cambió este ítem" });
  await expect(dialog.getByRole("region", { name: "Tus cambios" })).toContainText(
    "Segunda persona",
  );
  await expect(dialog.getByRole("region", { name: "Versión actual" })).toContainText(
    "Primera persona",
  );
  await expectNoA11yViolations(second.page);
  await dialog.getByRole("button", { name: "Conservar mis cambios" }).click();
  await expect(status(second.page, "Cambios guardados.")).toBeVisible();

  await first.page.reload();
  await expect(first.page.getByLabel("Enunciado")).toHaveValue(`Segunda persona (${code})`);
});
