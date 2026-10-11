/**
 * T077 y T083: importación en lote contra el stack e2e (US4 y US5; quickstart B14 a B16;
 * FR-028 a FR-036).
 * Las filas usan códigos propios de la prueba y el contexto LC-CTX-001 del banco inicial.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

import { type Page, expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { newItemCode, publishItems } from "./fixtures/content";
import { grantRole } from "./fixtures/db";
import { fillTemplate } from "./fixtures/xlsx";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test.describe.configure({ timeout: 180_000 });

interface SeedItem {
  id: string;
  competencia: string;
  afirmacion: string;
  evidencia: string;
  [field: string]: unknown;
}

async function seedItem(code: string): Promise<SeedItem> {
  const file = path.resolve(process.cwd(), "../backend/seeds/banco_inicial_saber_uli.json");
  const bank = JSON.parse(await readFile(file, "utf8")) as { items: SeedItem[] };
  const item = bank.items.find((entry) => entry.id === code);
  if (!item) throw new Error(`no está ${code} en el banco inicial`);
  return item;
}

async function teacher(page: Page): Promise<void> {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente importación" });
  grantRole(user.email, "teacher");
  await page.goto("/banco/importar");
  await expect(page.getByRole("heading", { name: "Importar ítems" })).toBeVisible();
}

function status(page: Page, text: string | RegExp) {
  return page.getByRole("status").filter({ hasText: text });
}

test("B14: plantilla con 20 válidos y 3 inválidos", async ({ page }) => {
  await teacher(page);
  const base = await seedItem("LC-0001");
  const prefix = newItemCode();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Descargar la plantilla" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("plantilla-banco-saber-uli.xlsx");
  const template = await readFile(await download.path());

  const rows = Array.from({ length: 23 }, (_, index) => {
    const number = String(index + 1).padStart(2, "0");
    const row: Record<string, unknown> = {
      id: `${prefix}-${number}`,
      modulo: "LC",
      competencia: base.competencia,
      afirmacion: base.afirmacion,
      evidencia: base.evidencia,
      dificultad: "media",
      origen: "docente",
      contexto_id: "LC-CTX-001",
      enunciado: `¿Qué afirma el autor? (${prefix} ${number})`,
      clave_correcta: "A",
      explicacion: "Se apoya en el texto.",
    };
    for (const key of "ABCD") {
      row[`opcion_${key}`] = `Opción ${key} de ${prefix} ${number}`;
      row[`retroalimentacion_${key}`] = `Porque ${key}.`;
    }
    return row;
  });
  rows[20]!.retroalimentacion_B = null;
  rows[21]!.afirmacion = "LC-A99";
  rows[22]!.clave_correcta = null;

  await page
    .getByLabel("Archivo (.json del banco o .xlsx de la plantilla, hasta 10 MB)")
    .setInputFiles({
      name: "plantilla-llena.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: fillTemplate(template, rows),
    });
  await page.getByRole("button", { name: "Validar el archivo" }).click();

  const counts = page.getByRole("list", { name: "Resultado de la validación" });
  await expect(counts.getByText("Nuevos: 20")).toBeVisible();
  await expect(counts.getByText("Con errores: 3")).toBeVisible();
  await page.getByLabel("Mostrar").selectOption("error");
  const table = page.getByRole("table", { name: "Filas del archivo" });
  for (const number of ["21", "22", "23"]) {
    await expect(table).toContainText(`${prefix}-${number}`);
  }
  await expect(table).not.toContainText(`${prefix}-20`);
  await expect(table).toContainText("Retroalimentación de la opción B");
  await expect(table).toContainText("Categoría inexistente");
  await expect(table).toContainText("Debe haber exactamente una opción correcta");
  await expectNoA11yViolations(page);

  const [report] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Descargar el reporte de errores" }).click(),
  ]);
  expect(report.suggestedFilename()).toMatch(/^reporte-importacion-.*\.xlsx$/);

  await page.getByRole("radio", { name: "En revisión" }).check();
  await page.getByRole("checkbox", { name: /son originales/ }).check();
  await page.getByRole("button", { name: "Confirmar importación" }).click();
  await expect(
    status(page, "Importación confirmada: 20 creados, 0 con versión nueva y 0 omitidos."),
  ).toBeVisible();

  await page.goto(`/banco/items/${prefix}-01`);
  await expect(page.getByLabel("Enunciado")).toHaveValue(`¿Qué afirma el autor? (${prefix} 01)`);
});

test("B15: un ítem igual a LC-0001 con otro código es un duplicado", async ({ page }) => {
  await teacher(page);
  const copy = { ...(await seedItem("LC-0001")), id: newItemCode(), estado: "borrador" };
  const file = JSON.stringify({ esquema_version: "1.0", items: [copy] });

  await page
    .getByLabel("Archivo (.json del banco o .xlsx de la plantilla, hasta 10 MB)")
    .setInputFiles({ name: "copia.json", mimeType: "application/json", buffer: Buffer.from(file) });
  await page.getByRole("button", { name: "Validar el archivo" }).click();

  await expect(
    page.getByRole("list", { name: "Resultado de la validación" }).getByText("Con errores: 1"),
  ).toBeVisible();
  const table = page.getByRole("table", { name: "Filas del archivo" });
  await expect(table).toContainText(copy.id);
  await expect(table).toContainText("Duplicado de un ítem del banco");
  await expect(page.getByText(/No hay ítems válidos para importar/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar importación" })).toHaveCount(0);
});

async function uploadFile(page: Page, name: string, content: string): Promise<void> {
  await page.goto("/banco/importar");
  await page
    .getByLabel("Archivo (.json del banco o .xlsx de la plantilla, hasta 10 MB)")
    .setInputFiles({ name, mimeType: "application/json", buffer: Buffer.from(content) });
  await page.getByRole("button", { name: "Validar el archivo" }).click();
}

async function confirmImport(page: Page, state: "Borrador" | "En revisión"): Promise<void> {
  await page.getByRole("radio", { name: state }).check();
  await page.getByRole("checkbox", { name: /son originales/ }).check();
  await page.getByRole("button", { name: "Confirmar importación" }).click();
}

test("B16: exportar, cambiar 3 y reimportar crea solo 3 versiones", async ({ page }) => {
  await teacher(page);
  const prefix = newItemCode();
  const sources = ["RC-0001", "RC-0002", "RC-0003", "RC-0004", "RC-0005"];
  const items = await Promise.all(
    Array.from({ length: 10 }, async (_, index) => {
      const base = await seedItem(sources[index % sources.length]!);
      const tag = `${prefix} ${index + 1}`;
      return {
        ...base,
        id: `${prefix}-${String(index + 1).padStart(2, "0")}`,
        enunciado: `${String(base.enunciado)} (${tag})`,
        opciones: (base.opciones as { texto: string }[]).map((option) => ({
          ...option,
          texto: `${option.texto} (${tag})`,
        })),
      };
    }),
  );
  await uploadFile(page, "nuevos.json", JSON.stringify({ esquema_version: "1.0", items }));
  await confirmImport(page, "En revisión");
  await expect(status(page, /10 creados/)).toBeVisible();
  publishItems(prefix);

  // Exportar lo publicado de RC en JSON.
  await page.goto("/banco/exportar");
  await page.getByLabel("Módulo").selectOption("RC");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Exportar" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^banco-saber-uli-.*\.json$/);
  const exported = JSON.parse(await readFile(await download.path(), "utf8")) as {
    items: { id: string; enunciado: string; version: number }[];
  };
  const ours = exported.items.filter((item) => item.id.startsWith(prefix));
  expect(ours).toHaveLength(10);
  for (const item of ours.slice(0, 3)) item.enunciado = `${item.enunciado} Versión corregida.`;
  const edited = JSON.stringify({ esquema_version: "1.0", items: ours });

  await uploadFile(page, "rc-editado.json", edited);
  const counts = page.getByRole("list", { name: "Resultado de la validación" });
  await expect(counts.getByText("Actualizaciones: 3")).toBeVisible();
  await expect(counts.getByText("Sin cambios: 7")).toBeVisible();
  await page.getByRole("button", { name: `Ver los cambios de ${prefix}-01 (1)` }).click();
  const changes = page.getByRole("table", { name: `Cambios de ${prefix}-01` });
  await expect(changes).toContainText("Enunciado");
  await expect(changes).toContainText("Versión corregida.");
  await expectNoA11yViolations(page);
  await confirmImport(page, "Borrador");
  await expect(
    status(page, "Importación confirmada: 0 creados, 3 con versión nueva y 0 omitidos."),
  ).toBeVisible();

  // El mismo archivo otra vez: nada que cambiar.
  await uploadFile(page, "rc-editado.json", edited);
  await expect(counts.getByText("Actualizaciones: 0")).toBeVisible();
  await expect(counts.getByText("Sin cambios: 10")).toBeVisible();
  await expect(page.getByText(/No hay ítems válidos para importar/)).toBeVisible();

  await page.goto(`/banco/items/${prefix}-01`);
  const versions = page.getByRole("list", { name: "Versiones" });
  await expect(versions.getByText(/Versión 2 · /)).toBeVisible();
  await expect(versions.getByText("Versión 1 · Publicado")).toBeVisible();
  await expect(versions).toContainText("Campos cambiados: Enunciado");
});
