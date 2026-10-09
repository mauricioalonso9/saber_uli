/**
 * T133: lote de 200 invitaciones contra el stack con perfil e2e (quickstart V9; FR-009; SC-005).
 *
 * Confirmar el lote encola 190 correos: mientras el worker los envía, los demás correos esperan
 * unos segundos. Por eso corre en el proyecto `estado-global`, después de las demás pruebas.
 */
import { type Browser, type Page, expect, test } from "@playwright/test";

import { newMockUser } from "./fixtures/auth";
import { onboardedUser } from "./fixtures/consent";
import { grantRole } from "./fixtures/db";

test.skip(
  ({ browserName }) => browserName === "webkit" && !process.env.E2E_OIDC_RESOLVES,
  "WebKit necesita `127.0.0.1 oidc` en el archivo hosts",
);

/** Docente con sesión privilegiada en `/invitaciones`. */
async function staffPage(browser: Browser, role: "teacher" | "admin"): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  const user = await onboardedUser(page, { ...newMockUser(), name: `Personal ${role}` });
  grantRole(user.email, role);
  await page.goto("/invitaciones");
  await expect(page.getByRole("heading", { name: "Invitaciones", level: 1 })).toBeVisible();
  return page;
}

test("V9: lote de 200 filas con reporte por fila en menos de 5 minutos (SC-005)", async ({
  browser,
}) => {
  const started = Date.now();
  const teacher = await staffPage(browser, "teacher");
  const prefix = crypto.randomUUID().slice(0, 6);
  const valid = Array.from({ length: 190 }, (_, i) => `lote-${prefix}-${i}@correo.co`);
  const lines = [
    "correo,nombre,vence",
    ...valid.map((email, i) => `${email},Persona ${i},`),
    ...Array.from({ length: 5 }, (_, i) => `no-es-correo-${i},,`),
    ...valid.slice(0, 3).map((email) => `${email.toUpperCase()},,`),
    "uno@unilibre.edu.co,,",
    "dos@est.unilibre.edu.co,,",
  ];
  const section = teacher.getByRole("region", { name: "Invitar por lote" });

  await section.getByLabel("Archivo CSV").setInputFiles({
    name: "invitados.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(lines.join("\n") + "\n", "utf-8"),
  });
  await section.getByRole("button", { name: "Revisar el archivo" }).click();

  await expect(section.getByText("190 válidas y 10 con problemas.")).toBeVisible();
  const report = section.getByRole("table", { name: "Reporte del lote" });
  await expect(report.getByRole("row")).toHaveCount(201);
  await expect(report.getByRole("row", { name: /no-es-correo-0.*Correo inválido/ })).toBeVisible();
  await expect(report.getByRole("row", { name: /Repetida en el archivo/ })).toHaveCount(3);
  await expect(report.getByRole("row", { name: /Correo institucional/ })).toHaveCount(2);

  await section.getByRole("button", { name: "Enviar 190 invitaciones" }).click();
  await expect(section.getByText("Enviamos 190 invitaciones.")).toBeVisible({ timeout: 30_000 });
  expect(Date.now() - started).toBeLessThan(5 * 60_000);
});
