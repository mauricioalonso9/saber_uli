/**
 * T070: vista previa y confirmación de una importación (US4; FR-030 a FR-036).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { ImportDetail } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ImportPreview } from "@/features/content/ImportPreviewPage";
import { importDetail } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const ID = importDetail().id;

function serveRows() {
  const actions: (string | null)[] = [];
  server.use(
    http.get(`/api/v1/content/imports/${ID}`, ({ request }) => {
      const action = new URL(request.url).searchParams.get("action");
      actions.push(action);
      const all = importDetail();
      return HttpResponse.json({
        ...all,
        rows: action ? all.rows.filter((row) => row.action === action) : all.rows,
      });
    }),
  );
  return actions;
}

function renderPreview(job: ImportDetail = importDetail()) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ImportPreview job={job} />
    </QueryClientProvider>,
  );
}

describe("vista previa de una importación", () => {
  it("muestra los conteos y avisa de los ítems de origen IA", async () => {
    serveRows();
    renderPreview();

    const counts = screen.getByRole("list", { name: "Resultado de la validación" });
    expect(within(counts).getByText("Nuevos: 2")).toBeInTheDocument();
    expect(within(counts).getByText("Sin cambios: 1")).toBeInTheDocument();
    expect(within(counts).getByText("Con errores: 1")).toBeInTheDocument();
    expect(
      await screen.findByText(/Hay ítems generados con IA: entrarán En revisión/),
    ).toBeInTheDocument();
  });

  it("filtra las filas y explica cada error con campo y regla legibles", async () => {
    const actions = serveRows();
    renderPreview();
    const user = userEvent.setup();

    await user.selectOptions(screen.getByLabelText("Mostrar"), "error");

    const table = await screen.findByRole("table", { name: "Filas del archivo" });
    const rows = await within(table).findAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(rows[1]).toHaveTextContent("LC-0104");
    expect(rows[1]).toHaveTextContent("Retroalimentación de la opción B");
    expect(rows[1]).toHaveTextContent("Falta la retroalimentación de una opción");
    expect(rows[1]).toHaveTextContent("La opción B necesita su retroalimentación.");
    expect(actions).toContain("error");
  });

  it("descarga el reporte de errores", async () => {
    serveRows();
    let downloaded = false;
    server.use(
      http.get(`/api/v1/content/imports/${ID}/report`, () => {
        downloaded = true;
        return new HttpResponse(new Uint8Array([80, 75]), {
          headers: {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          },
        });
      }),
    );
    renderPreview();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Descargar el reporte de errores" }));

    await vi.waitFor(() => expect(downloaded).toBe(true));
  });

  it("confirmar exige la declaración y el estado, y muestra el resultado", async () => {
    serveRows();
    let body: unknown = null;
    server.use(
      http.post(`/api/v1/content/imports/${ID}/confirmation`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          importDetail({
            status: "confirmed",
            confirmed_at: "2026-10-09T20:05:00Z",
            result: { created: 1, versioned: 0, skipped: ["LC-0102"] },
          }),
        );
      }),
    );
    renderPreview();
    const user = userEvent.setup();
    const confirm = screen.getByRole("button", { name: "Confirmar importación" });

    expect(confirm).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: "Borrador" }));
    expect(confirm).toBeDisabled();
    await user.click(
      screen.getByRole("checkbox", { name: /son originales y no reproducen preguntas del ICFES/ }),
    );
    await user.click(confirm);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Importación confirmada: 1 creados, 0 con versión nueva y 1 omitidos.",
    );
    expect(
      screen.getByText(/Omitidos porque cambiaron después de la vista previa: LC-0102/),
    ).toBeInTheDocument();
    expect(body).toEqual({ target_state: "draft", originality_declared: true });
  });

  it("una importación vencida no se puede confirmar", () => {
    serveRows();
    renderPreview(importDetail({ status: "expired" }));

    expect(screen.getByText(/venció/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar importación" })).not.toBeInTheDocument();
  });
});

/** T080: una reimportación con 1 actualización y 2 sin cambios (US5; FR-035). */
function updateDetail(): ImportDetail {
  const unchanged = (code: string) => ({
    code,
    entity: "item" as const,
    action: "unchanged" as const,
    target_state: null,
    changes: [],
    errors: [],
  });
  return importDetail({
    counts: { create: 0, update: 1, unchanged: 2, error: 0 },
    rows: [
      {
        code: "LC-0201",
        entity: "item",
        action: "update",
        target_state: null,
        changes: [
          { field: "difficulty", before: "medium", after: "high" },
          { field: "stem_md", before: "¿Qué sostiene el autor?", after: "¿Qué propone el autor?" },
          { field: "rubric_id", before: null, after: "R-1" },
        ],
        errors: [],
      },
      unchanged("LC-0202"),
      unchanged("LC-0203"),
    ],
    meta: { page: 1, page_size: 100, total: 3 },
  });
}

describe("vista previa de una actualización en lote", () => {
  beforeEach(() => {
    server.use(http.get(`/api/v1/content/imports/${ID}`, () => HttpResponse.json(updateDetail())));
  });

  it("despliega el antes y el después de cada campo de una actualización", async () => {
    renderPreview(updateDetail());
    const user = userEvent.setup();
    const toggle = await screen.findByRole("button", { name: "Ver los cambios de LC-0201 (3)" });

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("table", { name: "Cambios de LC-0201" })).not.toBeInTheDocument();
    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const changes = screen.getByRole("table", { name: "Cambios de LC-0201" });
    const rows = within(changes).getAllByRole("row");
    expect(rows[0]).toHaveTextContent("CampoAntesDespués");
    expect(rows[1]).toHaveTextContent("DificultadMediaAlta");
    expect(rows[2]).toHaveTextContent("Enunciado¿Qué sostiene el autor?¿Qué propone el autor?");
    expect(rows[3]).toHaveTextContent("Rúbrica(vacío)R-1");
  });

  it("agrupa los que no cambian en una sola fila", async () => {
    renderPreview(updateDetail());

    const table = await screen.findByRole("table", { name: "Filas del archivo" });
    await vi.waitFor(() => expect(within(table).getAllByRole("row")).toHaveLength(3));
    const rows = within(table).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("LC-0201");
    expect(rows[2]).toHaveTextContent("Sin cambios (2): LC-0202, LC-0203");
  });
});
