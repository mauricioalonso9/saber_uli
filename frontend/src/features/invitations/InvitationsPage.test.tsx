/**
 * T127: listado y acciones de invitaciones (FR-006, FR-010; escenarios 5.4 a 5.7).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { browser } from "@/features/auth/bootstrap";
import { useSessionStore } from "@/features/auth/session-store";
import { TEACHER_ID, invitation, renderInvitations } from "@/features/invitations/testing";

const SENT = invitation();
const ACCEPTED = invitation({
  id: "0192f3c4-0000-7000-8000-0000000000c2",
  email: "pedro@correo.co",
  invitee_name: null,
  status: "accepted",
  accepted_at: "2026-10-08T15:00:00Z",
});

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
  vi.restoreAllMocks();
});
afterAll(() => server.close());

let queries: URLSearchParams[];
let revoked: string[];

function mockList() {
  queries = [];
  revoked = [];
  server.use(
    http.get("/api/v1/invitations", ({ request }) => {
      queries.push(new URL(request.url).searchParams);
      return HttpResponse.json({ page: 1, page_size: 25, total: 2, items: [SENT, ACCEPTED] });
    }),
    http.post("/api/v1/invitations/:id/revocation", ({ params }) => {
      revoked.push(String(params.id));
      return HttpResponse.json({ ...ACCEPTED, status: "revoked" });
    }),
  );
}

describe("listado de invitaciones", () => {
  it("muestra cada invitación con su estado y vencimiento", async () => {
    mockList();
    renderInvitations("teacher");

    const table = await screen.findByRole("table", { name: /invitaciones enviadas/i });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("laura@correo.co");
    expect(rows[0]).toHaveTextContent("Laura Gómez");
    expect(rows[0]).toHaveTextContent("Enviada");
    expect(rows[0]).toHaveTextContent("4 de enero de 2027");
    expect(rows[1]).toHaveTextContent("Aceptada");
  });

  it("filtra por estado", async () => {
    mockList();
    renderInvitations("teacher");
    const user = userEvent.setup();

    await user.selectOptions(await screen.findByRole("combobox", { name: "Estado" }), "Revocada");

    await vi.waitFor(() => expect(queries.at(-1)?.get("status")).toBe("revoked"));
  });

  it("el docente no tiene el filtro por quién invitó", async () => {
    mockList();
    renderInvitations("teacher");

    await screen.findByRole("table", { name: /invitaciones enviadas/i });
    expect(screen.queryByRole("checkbox", { name: /solo las que yo envié/i })).toBeNull();
    expect(queries.every((query) => !query.has("invited_by"))).toBe(true);
  });

  it("el administrador puede ver solo las suyas", async () => {
    mockList();
    renderInvitations("admin");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("checkbox", { name: /solo las que yo envié/i }));

    await vi.waitFor(() => expect(queries.at(-1)?.get("invited_by")).toBe(TEACHER_ID));
    expect(await screen.findByRole("columnheader", { name: /invitó/i })).toBeInTheDocument();
  });

  it("ofrece las acciones según el estado de cada invitación", async () => {
    mockList();
    renderInvitations("teacher");

    const table = await screen.findByRole("table", { name: /invitaciones enviadas/i });
    const [sent, accepted] = within(table).getAllByRole("row").slice(1);
    expect(within(sent!).getByRole("button", { name: /reenviar/i })).toBeInTheDocument();
    expect(within(sent!).getByRole("button", { name: /revocar/i })).toBeInTheDocument();
    expect(within(accepted!).queryByRole("button", { name: /reenviar/i })).toBeNull();
    expect(
      within(accepted!).getByRole("button", { name: /cambiar vencimiento/i }),
    ).toBeInTheDocument();
  });

  it("revocar pide confirmación y luego revoca", async () => {
    mockList();
    renderInvitations("teacher");
    const user = userEvent.setup();
    const table = await screen.findByRole("table", { name: /invitaciones enviadas/i });
    const accepted = within(table).getAllByRole("row")[2]!;

    await user.click(within(accepted).getByRole("button", { name: /revocar/i }));
    const dialog = screen.getByRole("alertdialog", { name: /revocar el acceso/i });
    expect(dialog).toHaveTextContent(/pedro@correo.co/);
    await user.click(within(dialog).getByRole("button", { name: "Sí, revocar" }));

    await vi.waitFor(() => expect(revoked).toEqual([ACCEPTED.id]));
    expect(await screen.findByText(/revocamos el acceso/i)).toBeInTheDocument();
  });

  it("sin sesión privilegiada pide confirmar la identidad", async () => {
    server.use(
      http.get("/api/v1/invitations", () =>
        HttpResponse.json(
          {
            type: "urn:saber-uli:problem:reauthentication-required",
            title: "No autenticado",
            status: 401,
          },
          { status: 401, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const assign = vi.spyOn(browser, "assign").mockImplementation(() => undefined);
    renderInvitations("teacher");
    const user = userEvent.setup();

    expect(await screen.findByRole("alert")).toHaveTextContent(/confirma tu identidad/i);
    await user.click(screen.getByRole("button", { name: "Confirmar mi identidad" }));

    expect(assign).toHaveBeenCalledWith("/api/auth/microsoft/login?return_to=%2Finvitaciones");
  });
});
