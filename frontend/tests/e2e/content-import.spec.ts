/**
 * T077: importación en lote contra el stack e2e (US4; quickstart B14 y B15; FR-028 a FR-036).
 * Las filas usan códigos propios de la prueba y el contexto LC-CTX-001 del banco inicial.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

import { type Page, expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { newItemCode } from "./fixtures/content";
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
