/**
 * T170: consultar, descargar y corregir mis datos contra el stack con perfil e2e (US8;
 * quickstart V17; FR-031; escenarios 8.1 y 8.2).
 */
import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { expectNoA11yViolations } from "./fixtures/axe";
import { onboardedUser } from "./fixtures/consent";
import { addToGroup, ensureProgram } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

const PROGRAM = { code: "E2E-DER", name: "Derecho E2E", campus: "Bogotá" };

test.beforeAll(() => {
  ensureProgram(PROGRAM.code, PROGRAM.name, PROGRAM.campus);
});

test("V17: ver, descargar y validar mis datos, y corregir el perfil", async ({ page }) => {
  const user = await onboardedUser(page, { ...newMockUser(), name: "Persona V17" });
  const group = `Grupo V17 ${crypto.randomUUID().slice(0, 6)}`;
  addToGroup(user.email, group);

  // Corrige un dato editable del perfil (escenario 8.2: el enlace lleva a Mi cuenta).
  await page.goto("/mi-cuenta/datos");
  const note = page.getByRole("note", { name: /algún dato está mal/i });
  await expect(note).toContainText("directorio institucional");
  await expectNoA11yViolations(page);
  await note.getByRole("link", { name: "Editar mi perfil" }).click();
  await expect(page.getByRole("heading", { name: "Mi cuenta", exact: true })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Programa académico" })
    .selectOption({ label: `${PROGRAM.name} (${PROGRAM.campus})` });
  await page.getByRole("combobox", { name: "Semestre" }).selectOption("6");
  // `onboardedUser` da por completo el perfil en la base: aquí se llenan los demás campos.
  await page.getByLabel("Fecha estimada de tu prueba Saber Pro").fill("2027-05-30");
  await page.getByRole("radio", { name: "Intensa" }).check();
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByText("Guardamos tus cambios.")).toBeVisible();

  // Lo ve en Mis datos (escenario 8.1).
  await page.goto("/mi-cuenta/datos");
  await expect(page.getByRole("region", { name: "Identidad" })).toContainText(user.email);
  const profile = page.getByRole("region", { name: "Perfil" });
  await expect(profile).toContainText(`${PROGRAM.name} (${PROGRAM.campus})`);
  await expect(profile).toContainText("6");
  await expect(page.getByRole("region", { name: "Grupos" })).toContainText(group);

  // Descarga la copia y valida el JSON.
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Descargar una copia" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^saber-uli-mis-datos-\d{4}-\d{2}-\d{2}\.json$/);
  const data = JSON.parse(await readFile(await download.path(), "utf8")) as {
    identity: { email: string; display_name: string; kind: string; source_note: string };
    profile: { semester: number; program: { name: string } };
    roles: string[];
    groups: string[];
    consents: { decision: string }[];
  };
  expect(data.identity).toMatchObject({
    email: user.email,
    display_name: user.name,
    kind: "institutional",
  });
  expect(data.identity.source_note).toContain("directorio");
  expect(data.profile.semester).toBe(6);
  expect(data.profile.program.name).toBe(PROGRAM.name);
  expect(data.roles).toEqual(["student"]);
  expect(data.groups).toEqual([group]);
  expect(data.consents.map((consent) => consent.decision)).toEqual(["accepted"]);
});
