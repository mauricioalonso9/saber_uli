/**
 * T080: historia de un ítem (US5; FR-018): cada versión con estado, autor, revisor, fechas y
 * campos cambiados, y los eventos con quién y cuándo.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { ItemHistory as History } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ItemHistory } from "@/features/content/ItemHistory";
import { formatDateTime } from "@/shared/lib/dates";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const TEACHER = { id: "u-1", display_name: "Docente Uno" };
const ADMIN = { id: "u-2", display_name: "Admin Dos" };

const HISTORY: History = {
  versions: [
    {
      number: 1,
      state: "retired",
      author: TEACHER,
      reviewer: ADMIN,
      created_at: "2026-10-01T15:00:00Z",
      published_at: "2026-10-02T15:00:00Z",
      retired_at: "2026-10-09T15:00:00Z",
      changed_fields: [],
    },
    {
      number: 2,
      state: "published",
      author: TEACHER,
      reviewer: ADMIN,
      created_at: "2026-10-08T15:00:00Z",
      published_at: "2026-10-09T15:00:00Z",
      retired_at: null,
      changed_fields: ["stem_md", "options[B].feedback"],
    },
  ],
  events: [
    {
      id: "e-1",
      type: "imported",
      version: 2,
      actor: TEACHER,
      occurred_at: "2026-10-08T15:00:00Z",
      comment: null,
      reason: null,
      details: {},
    },
    {
      id: "e-2",
      type: "superseded",
      version: 1,
      actor: ADMIN,
      occurred_at: "2026-10-09T15:00:00Z",
      comment: null,
      reason: null,
      details: {},
    },
    {
      id: "e-3",
      type: "returned",
      version: 2,
      actor: null,
      occurred_at: "2026-10-09T14:00:00Z",
      comment: "Revisa la opción B",
      reason: null,
      details: {},
    },
  ],
};

function renderHistory() {
  server.use(http.get("/api/v1/content/items/LC-0001/history", () => HttpResponse.json(HISTORY)));
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ItemHistory code="LC-0001" />
    </QueryClientProvider>,
  );
}

describe("historia de un ítem", () => {
  it("muestra cada versión, la más reciente primero, con su estado, personas y fechas", async () => {
    renderHistory();

    const versions = await screen.findByRole("list", { name: "Versiones" });
    const [latest, first] = within(versions).getAllByRole("listitem");
    expect(latest).toHaveTextContent("Versión 2 · Publicado");
    expect(latest).toHaveTextContent("Autor: Docente Uno");
    expect(latest).toHaveTextContent("Revisó: Admin Dos");
    expect(latest).toHaveTextContent(`Creada: ${formatDateTime("2026-10-08T15:00:00Z")}`);
    expect(latest).toHaveTextContent(`Publicada: ${formatDateTime("2026-10-09T15:00:00Z")}`);
    expect(latest).toHaveTextContent(
      "Campos cambiados: Enunciado, Retroalimentación de la opción B",
    );
    expect(first).toHaveTextContent("Versión 1 · Retirado");
    expect(first).toHaveTextContent(`Retirada: ${formatDateTime("2026-10-09T15:00:00Z")}`);
    expect(first).toHaveTextContent("Primera versión");
  });

  it("muestra los eventos con quién, cuándo y el comentario", async () => {
    renderHistory();

    const events = await screen.findByRole("list", { name: "Eventos" });
    const items = within(events).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Importado · versión 2 · Docente Uno");
    expect(items[1]).toHaveTextContent("Reemplazado por una versión nueva · versión 1 · Admin Dos");
    expect(items[2]).toHaveTextContent("Devuelto con comentarios · versión 2 · Sistema");
    expect(items[2]).toHaveTextContent("Revisa la opción B");
  });
});
