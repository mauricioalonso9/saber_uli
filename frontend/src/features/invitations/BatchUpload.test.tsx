/**
 * T127: carga de un lote de invitaciones (FR-009; escenario 5.2).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import type { InvitationBatch } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import { renderInvitations } from "@/features/invitations/testing";

const CSV = "correo,nombre,vence\nlaura@correo.co,Laura,\nno-es-correo,,\nana@unilibre.edu.co,,\n";

const REPORT: InvitationBatch = {
  id: "0192f3c4-0000-7000-8000-0000000000d1",
  status: "pending_confirmation",
  valid_count: 1,
  invalid_count: 2,
  expires_at: "2026-10-08T15:00:00Z",
  rows: [
    { line: 2, email: "laura@correo.co", name: "Laura", result: "valid" },
    { line: 3, email: "no-es-correo", result: "invalid_email", message: "El correo no es válido." },
    {
      line: 4,
      email: "ana@unilibre.edu.co",
      result: "institutional_email",
      message: "Es un correo de Unilibre: ingresa con su cuenta institucional.",
    },
  ],
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let uploads: { type: string | null; body: string }[];
let confirmations: string[];

function mockApi() {
  uploads = [];
  confirmations = [];
  server.use(
    http.get("/api/v1/invitations", () =>
      HttpResponse.json({ page: 1, page_size: 25, total: 0, items: [] }),
    ),
    http.post("/api/v1/invitation-batches", async ({ request }) => {
      uploads.push({ type: request.headers.get("content-type"), body: await request.text() });
      return HttpResponse.json(REPORT, { status: 201 });
    }),
    http.post("/api/v1/invitation-batches/:id/confirmation", ({ params }) => {
      confirmations.push(String(params.id));
      return HttpResponse.json({
        ...REPORT,
        status: "confirmed",
        confirmed_at: "2026-10-07T16:00:00Z",
      });
    }),
  );
}

async function uploadFile() {
  const user = userEvent.setup();
  const section = await screen.findByRole("region", { name: /invitar por lote/i });
  await user.upload(
    within(section).getByLabelText("Archivo CSV"),
    new File([CSV], "invitados.csv", { type: "text/csv" }),
  );
  await user.click(within(section).getByRole("button", { name: "Revisar el archivo" }));
  return { user, section };
}

describe("lote de invitaciones", () => {
  it("envía el CSV tal cual y muestra el reporte por fila", async () => {
    mockApi();
    renderInvitations("teacher");

    const { section } = await uploadFile();

    const report = await within(section).findByRole("table", { name: /reporte del lote/i });
    const rows = within(report).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringMatching(/2.*laura@correo\.co.*Válida/),
      expect.stringMatching(/3.*no-es-correo.*Correo inválido.*no es válido/),
      expect.stringMatching(/4.*ana@unilibre\.edu\.co.*Correo institucional/),
    ]);
    expect(section).toHaveTextContent(/1 válida y 2 con problemas/i);
    expect(uploads).toEqual([{ type: "text/csv", body: CSV }]);
  });

  it("confirma y envía solo las válidas", async () => {
    mockApi();
    renderInvitations("teacher");
    const { user, section } = await uploadFile();

    await user.click(await within(section).findByRole("button", { name: "Enviar 1 invitación" }));

    expect(await within(section).findByText(/enviamos 1 invitación/i)).toBeInTheDocument();
    expect(confirmations).toEqual([REPORT.id]);
  });

  it("explica cuando el archivo tiene demasiadas filas", async () => {
    mockApi();
    server.use(
      http.post("/api/v1/invitation-batches", () =>
        HttpResponse.json(
          {
            type: "urn:saber-uli:problem:batch-too-large",
            title: "Error",
            status: 413,
            detail: "El lote admite hasta 500 filas.",
          },
          { status: 413, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    renderInvitations("teacher");

    const { section } = await uploadFile();

    expect(await within(section).findByRole("alert")).toHaveTextContent(/demasiadas filas/i);
  });
});
