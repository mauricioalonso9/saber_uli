/**
 * T086: exportación del banco (US6; FR-038): filtros, formato, versión y el aviso de los ítems
 * que no caben en la plantilla (`X-Skipped-Items`).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import { useSessionStore } from "@/features/auth/session-store";
import { ExportPage } from "@/features/content/ExportPage";
import { MODULES } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => {
  useSessionStore.getState().setSession("token", 600);
  server.use(http.get("/api/v1/content/modules", () => HttpResponse.json({ items: MODULES })));
});
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function serveExport(skipped: number) {
  const queries: URLSearchParams[] = [];
  server.use(
    http.get("/api/v1/content/export", ({ request }) => {
      const params = new URL(request.url).searchParams;
      queries.push(params);
      const xlsx = params.get("format") === "xlsx";
      return new HttpResponse(xlsx ? new Uint8Array([80, 75]) : '{"items": []}', {
        headers: {
          "Content-Type": xlsx ? XLSX : "application/json",
          "Content-Disposition": `attachment; filename="banco.${xlsx ? "xlsx" : "json"}"`,
          "X-Skipped-Items": String(skipped),
        },
      });
    }),
  );
  return queries;
}

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ExportPage />
    </QueryClientProvider>,
  );
}

describe("exportación del banco", () => {
  it("exporta en JSON lo publicado sin filtros por omisión", async () => {
    const queries = serveExport(0);
    renderPage();
    const user = userEvent.setup();

    expect(screen.getByRole("radio", { name: "JSON (formato del banco)" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "La versión publicada" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Exportar" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Se descargó banco.json.");
    expect(Object.fromEntries(queries[0]!)).toEqual({ format: "json", version: "published" });
  });

  it("envía los filtros, el formato y la versión elegidos", async () => {
    const queries = serveExport(0);
    renderPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("radio", { name: "Hoja de cálculo (plantilla .xlsx)" }));
    await user.click(screen.getByRole("radio", { name: "La última versión de cada ítem" }));
    await screen.findByRole("option", { name: "Lectura crítica" });
    await user.selectOptions(screen.getByLabelText("Módulo"), "LC");
    await user.selectOptions(screen.getByLabelText("Estado"), "in_review");
    await user.selectOptions(screen.getByLabelText("Origen"), "ai");
    await user.selectOptions(screen.getByLabelText("Dificultad"), "high");
    await user.selectOptions(await screen.findByLabelText("Categoría"), "lc-a1");
    await user.click(screen.getByRole("button", { name: "Exportar" }));

    await screen.findByRole("status");
    expect(Object.fromEntries(queries[0]!)).toEqual({
      format: "xlsx",
      version: "latest",
      module: "LC",
      state: "in_review",
      origin: "ai",
      difficulty: "high",
      taxonomy_node: "lc-a1",
    });
  });

  it("la categoría solo aparece con un módulo elegido", async () => {
    renderPage();
    const user = userEvent.setup();

    expect(screen.queryByLabelText("Categoría")).not.toBeInTheDocument();
    await screen.findByRole("option", { name: "Inglés" });
    await user.selectOptions(screen.getByLabelText("Módulo"), "ING");
    const category = await screen.findByLabelText("Categoría");
    expect(category).toHaveTextContent("Parte 2");
    expect(category).not.toHaveTextContent("Comprensión");
  });

  it("avisa cuántos ítems no caben en la plantilla", async () => {
    serveExport(8);
    renderPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("radio", { name: "Hoja de cálculo (plantilla .xlsx)" }));
    await user.click(screen.getByRole("button", { name: "Exportar" }));

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("Se descargó banco.xlsx.");
    expect(status).toHaveTextContent(
      "8 ítems no caben en la plantilla (consignas, emparejamiento de Inglés parte 1 y contextos con imagen o tabla). Para incluirlos, exporta en JSON.",
    );
  });

  it("muestra el error si la exportación falla", async () => {
    server.use(
      http.get("/api/v1/content/export", () =>
        HttpResponse.json(
          { type: "https://saber-uli.unilibre.edu.co/problems/forbidden", title: "Prohibido" },
          { status: 403 },
        ),
      ),
    );
    renderPage();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Exportar" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
