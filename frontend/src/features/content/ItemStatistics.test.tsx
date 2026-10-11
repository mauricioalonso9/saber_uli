/**
 * T098: estadísticas de un ítem por versión (US8; FR-041 a FR-043): "aún no hay datos
 * suficientes", cifras en es-CO, señales explicadas y barras por opción con su valor en texto.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { VersionStatistics } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ItemStatistics } from "@/features/content/ItemStatistics";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const NEW: VersionStatistics = {
  version: 2,
  state: "published",
  first_responses: 12,
  sufficient_data: false,
  correct_rate: null,
  option_rates: null,
  discrimination: null,
  signals: [],
  computed_at: "2026-10-10T08:00:00Z",
};

const OLD: VersionStatistics = {
  version: 1,
  state: "retired",
  first_responses: 1250,
  sufficient_data: true,
  correct_rate: 0.125,
  option_rates: { A: 0.125, B: 0.6, C: 0.2, D: 0.075 },
  discrimination: -0.1234,
  signals: ["too_hard", "negative_discrimination", "distractor_beats_key"],
  computed_at: "2026-10-10T08:00:00Z",
};

function renderStatistics(items: VersionStatistics[] = [NEW, OLD]) {
  server.use(
    http.get("/api/v1/content/items/LC-0001/statistics", () => HttpResponse.json({ items })),
  );
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ItemStatistics code="LC-0001" />
    </QueryClientProvider>,
  );
}

describe("estadísticas de un ítem", () => {
  it("con menos de 30 respuestas dice que aún no hay datos suficientes", async () => {
    renderStatistics();

    const latest = await screen.findByRole("region", { name: "Versión 2 · Publicado" });
    expect(latest).toHaveTextContent(
      "Aún no hay datos suficientes: 12 respuestas (se necesitan al menos 30).",
    );
    expect(within(latest).queryByText(/Acierto/)).not.toBeInTheDocument();
  });

  it("muestra las cifras con formato es-CO", async () => {
    renderStatistics();

    const old = await screen.findByRole("region", { name: "Versión 1 · Retirado" });
    expect(old).toHaveTextContent("Respuestas: 1.250");
    expect(old).toHaveTextContent(/Acierto: 12,5\s?%/u);
    expect(old).toHaveTextContent("Discriminación: -0,12");
  });

  it("explica cada señal de problema en texto", async () => {
    renderStatistics();

    const signals = await screen.findByRole("list", {
      name: "Señales de problema de la versión 1",
    });
    const items = within(signals).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Muy difícil: acierta menos del 20 %.",
      "Discriminación negativa: aciertan más quienes tienen peor desempeño en el resto del módulo.",
      "Una opción incorrecta se elige más que la correcta.",
    ]);
  });

  it("las barras por opción llevan su valor en texto y no tienen violaciones de axe", async () => {
    const { container } = renderStatistics([OLD]);

    const options = await screen.findByRole("list", { name: "Elección de cada opción, versión 1" });
    const rows = within(options).getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(rows[1]).toHaveTextContent(/^B60\s?%$/u);
    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(result.violations).toEqual([]);
  });

  it("sin versiones publicadas lo dice", async () => {
    renderStatistics([]);

    expect(await screen.findByText("Este ítem aún no tiene versiones publicadas.")).toBeVisible();
  });
});
