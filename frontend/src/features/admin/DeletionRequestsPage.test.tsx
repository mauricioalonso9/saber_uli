/**
 * T157: solicitudes de supresión para el administrador (FR-034; escenario 7.4).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { DeletionRequest } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import { page, renderAt } from "@/features/admin/testing";

const RECEIVED: DeletionRequest = {
  id: "0192f3c4-0000-7000-8000-0000000000e1",
  user_id: "0192f3c4-0000-7000-8000-0000000000f1",
  status: "received",
  origin: "user_request",
  requested_at: "2026-10-06T17:00:00Z",
  due_date: "2026-10-28",
};

const COMPLETED: DeletionRequest = {
  id: "0192f3c4-0000-7000-8000-0000000000e2",
  user_id: "0192f3c4-0000-7000-8000-0000000000f2",
  status: "completed",
  origin: "guest_retention",
  requested_at: "2026-10-01T07:00:00Z",
  due_date: "2026-10-23",
  completed_at: "2026-10-01T07:15:00Z",
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let queries: string[];

function serve(items: DeletionRequest[]) {
  queries = [];
  server.use(
    http.get("/api/v1/admin/deletion-requests", ({ request }) => {
      queries.push(new URL(request.url).search);
      return HttpResponse.json(page(items));
    }),
  );
}

describe("solicitudes de supresión", () => {
  it("muestra estado, origen y fecha límite de cada solicitud", async () => {
    serve([RECEIVED, COMPLETED]);
    renderAt("/admin/supresiones");

    const table = await screen.findByRole("table", { name: "Solicitudes de supresión" });
    const [, first, second] = within(table).getAllByRole("row");
    expect(first).toHaveTextContent("Recibida");
    expect(first).toHaveTextContent("Solicitud de la persona");
    expect(first).toHaveTextContent("28 de octubre de 2026");
    expect(second).toHaveTextContent("Completada");
    expect(second).toHaveTextContent("Conservación de invitado");
    expect(second).toHaveTextContent("23 de octubre de 2026");
  });

  it("filtra por estado", async () => {
    serve([COMPLETED]);
    renderAt("/admin/supresiones");
    const user = userEvent.setup();

    await screen.findByRole("table", { name: "Solicitudes de supresión" });
    await user.selectOptions(screen.getByRole("combobox", { name: "Estado" }), "completed");

    await vi.waitFor(() => {
      expect(new URLSearchParams(queries.at(-1)).get("status")).toBe("completed");
    });
  });

  it("aparece en el menú del administrador", async () => {
    serve([]);
    renderAt("/admin/supresiones");

    const nav = await screen.findByRole("navigation", { name: "Principal" });
    expect(within(nav).getByRole("link", { name: "Supresiones" })).toBeInTheDocument();
    expect(await screen.findByText(/no hay solicitudes/i)).toBeInTheDocument();
  });
});
