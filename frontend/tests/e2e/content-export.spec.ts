/**
 * T089: exportación del banco contra el stack e2e (US6; quickstart B17; FR-038, SC-008).
 * La ida y vuelta usa Competencias ciudadanas, que ninguna otra prueba cambia.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";

import { type Page, expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { newItemCode, publishItems } from "./fixtures/content";
import { grantRole } from "./fixtures/db";
import { readItemRows } from "./fixtures/xlsx";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

test.describe.configure({ timeout: 180_000 });

async function teacher(page: Page): Promise<void> {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Docente exportación" });
  grantRole(user.email, "teacher");
  await page.goto("/banco/exportar");
  await expect(page.getByRole("heading", { name: "Exportar el banco" })).toBeVisible();
}

async function exportFile(page: Page): Promise<Buffer> {
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Exportar" }).click(),
  ]);
  return readFile(await download.path());
}

test("B17: Inglés en XLSX deja fuera la parte 1 y lo informa", async ({ page }) => {
  await teacher(page);
  await page.getByRole("radio", { name: "Hoja de cálculo (plantilla .xlsx)" }).check();
  await page.getByRole("radio", { name: "La última versión de cada ítem" }).check();
  await page.getByLabel("Módulo").selectOption("ING");

  const file = await exportFile(page);

  const status = page.getByRole("status").filter({ hasText: "Se descargó" });
  await expect(status).toContainText(/Se descargó banco-saber-uli-.*\.xlsx\./);
  const skipped = Number(
    /(\d+) ítems no caben en la plantilla/.exec(await status.innerText())?.[1],
  );
  expect(skipped).toBeGreaterThanOrEqual(5); // ING-0001 a ING-0005, emparejamiento
  const rows = readItemRows(file);
  expect(rows.length).toBeGreaterThan(0);
  for (const row of rows) {
    expect(row.modulo).toBe("ING");
    expect(Number(row.parte)).toBeGreaterThanOrEqual(2);
  }
  expect(rows.map((row) => row.id)).not.toContain("ING-0001");
  await expectNoA11yViolations(page);
});

test("reimportar lo exportado no cambia nada (SC-008)", async ({ page }) => {
  await teacher(page);
  const prefix = newItemCode();
  const seedFile = path.resolve(process.cwd(), "../backend/seeds/banco_inicial_saber_uli.json");
  const bank = JSON.parse(await readFile(seedFile, "utf8")) as {
    items: { id: string; modulo: string; enunciado: string; opciones: { texto: string }[] }[];
  };
  const items = bank.items
    .filter((item) => item.modulo === "CC")
    .slice(0, 4)
    .map((item, index) => ({
      ...item,
      id: `${prefix}-${index + 1}`,
      enunciado: `${item.enunciado} (${prefix})`,
      opciones: item.opciones.map((option) => ({
        ...option,
        texto: `${option.texto} (${prefix})`,
      })),
    }));
  await page.goto("/banco/importar");
  await page
    .getByLabel("Archivo (.json del banco o .xlsx de la plantilla, hasta 10 MB)")
    .setInputFiles({
      name: "cc.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify({ esquema_version: "1.0", items })),
    });
  await page.getByRole("button", { name: "Validar el archivo" }).click();
  await page.getByRole("radio", { name: "En revisión" }).check();
  await page.getByRole("checkbox", { name: /son originales/ }).check();
  await page.getByRole("button", { name: "Confirmar importación" }).click();
  await expect(page.getByRole("status").filter({ hasText: /4 creados/ })).toBeVisible();
  publishItems(prefix);

  await page.goto("/banco/exportar");
  await page.getByLabel("Módulo").selectOption("CC");
  const file = await exportFile(page);
  const exported = JSON.parse(file.toString("utf8")) as { items: { id: string }[] };
  expect(exported.items.filter((item) => item.id.startsWith(prefix))).toHaveLength(4);

  await page.goto("/banco/importar");
  await page
    .getByLabel("Archivo (.json del banco o .xlsx de la plantilla, hasta 10 MB)")
    .setInputFiles({ name: "exportado.json", mimeType: "application/json", buffer: file });
  await page.getByRole("button", { name: "Validar el archivo" }).click();

  const counts = page.getByRole("list", { name: "Resultado de la validación" });
  await expect(counts.getByText("Nuevos: 0")).toBeVisible();
  await expect(counts.getByText("Actualizaciones: 0")).toBeVisible();
  await expect(counts.getByText("Con errores: 0")).toBeVisible();
});
