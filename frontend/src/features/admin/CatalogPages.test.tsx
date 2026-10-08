/**
 * T142: programas (FR-028), parámetros (FR-006a) y auditoría (FR-035).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { AuditEvent, Program, Settings } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ME_ID, page, renderAt } from "@/features/admin/testing";

const DERECHO: Program = {
  id: "0192f3c4-0000-7000-8000-0000000000b1",
  code: "DER-BOG",
  name: "Derecho",
  campus: "Bogotá",
  active: true,
};

const SETTINGS: Settings = {
  teacher_max_access_days: 180,
  default_guest_access_days: 90,
  invitation_link_ttl_days: 7,
  sign_in_link_ttl_minutes: 15,
};

const EVENT: AuditEvent = {
  id: "0192f3c4-0000-7000-8000-0000000000d1",
  occurred_at: "2026-10-07T15:30:00Z",
  actor_id: ME_ID,
  action: "setting.changed",
  target_type: "setting",
  details: { key: "teacher_max_access_days", before: 180, after: 120 },
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let sent: { method: string; path: string; body?: unknown; query: string }[];

async function record(request: Request) {
  const url = new URL(request.url);
  const body = request.method === "GET" ? undefined : await request.json();
  sent.push({ method: request.method, path: url.pathname, body, query: url.search });
}

describe("programas", () => {
  function mockPrograms() {
    sent = [];
    server.use(
      http.get("/api/v1/admin/programs", () => HttpResponse.json(page([DERECHO]))),
      http.post("/api/v1/admin/programs", async ({ request }) => {
        await record(request);
        return HttpResponse.json({ ...DERECHO, id: "nuevo", code: "CON-CAL" }, { status: 201 });
      }),
      http.patch("/api/v1/admin/programs/:id", async ({ request }) => {
        await record(request);
        return HttpResponse.json({ ...DERECHO, active: false });
      }),
    );
  }

  it("lista, crea y desactiva programas", async () => {
    mockPrograms();
    renderAt("/admin/programas");
    const user = userEvent.setup();

    const table = await screen.findByRole("table", { name: "Programas" });
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("DER-BOG");
    const form = screen.getByRole("form", { name: "Crear un programa" });
    await user.type(within(form).getByRole("textbox", { name: "Código" }), "CON-CAL");
    await user.type(within(form).getByRole("textbox", { name: "Nombre" }), "Contaduría");
    await user.type(within(form).getByRole("textbox", { name: "Seccional" }), "Cali");
    await user.click(within(form).getByRole("button", { name: "Crear programa" }));
    await user.click(await screen.findByRole("button", { name: "Desactivar Derecho (Bogotá)" }));

    await vi.waitFor(() =>
      expect(sent).toEqual([
        expect.objectContaining({
          method: "POST",
          body: { code: "CON-CAL", name: "Contaduría", campus: "Cali" },
        }),
        expect.objectContaining({ method: "PATCH", body: { active: false } }),
      ]),
    );
  });

  it("valida el código antes de enviar", async () => {
    mockPrograms();
    renderAt("/admin/programas");
    const user = userEvent.setup();
    const form = await screen.findByRole("form", { name: "Crear un programa" });

    await user.type(within(form).getByRole("textbox", { name: "Código" }), "der bog");
    await user.type(within(form).getByRole("textbox", { name: "Nombre" }), "Derecho");
    await user.type(within(form).getByRole("textbox", { name: "Seccional" }), "Bogotá");
    await user.click(within(form).getByRole("button", { name: "Crear programa" }));

    expect(within(form).getByRole("textbox", { name: "Código" })).toHaveAccessibleDescription(
      /mayúsculas, números o guiones/i,
    );
    expect(sent).toEqual([]);
  });
});

describe("parámetros", () => {
  function mockSettings() {
    sent = [];
    server.use(
      http.get("/api/v1/admin/settings", () => HttpResponse.json(SETTINGS)),
      http.patch("/api/v1/admin/settings", async ({ request }) => {
        await record(request);
        return HttpResponse.json({ ...SETTINGS, teacher_max_access_days: 120 });
      }),
    );
  }

  it("envía solo lo que cambió", async () => {
    mockSettings();
    renderAt("/admin/parametros");
    const user = userEvent.setup();

    const field = await screen.findByRole("spinbutton", { name: /plazo máximo para docentes/i });
    expect(field).toHaveValue(180);
    await user.clear(field);
    await user.type(field, "120");
    await user.click(screen.getByRole("button", { name: "Guardar parámetros" }));

    expect(await screen.findByText(/guardamos los parámetros/i)).toBeInTheDocument();
    expect(sent).toEqual([expect.objectContaining({ body: { teacher_max_access_days: 120 } })]);
  });

  it("respeta los rangos permitidos", async () => {
    mockSettings();
    renderAt("/admin/parametros");
    const user = userEvent.setup();

    const field = await screen.findByRole("spinbutton", { name: /enlace de ingreso/i });
    await user.clear(field);
    await user.type(field, "4");
    await user.click(screen.getByRole("button", { name: "Guardar parámetros" }));

    expect(field).toHaveAccessibleDescription(/entre 5 y 60/i);
    expect(sent).toEqual([]);
  });
});

describe("auditoría", () => {
  it("muestra los eventos y filtra por acción y fechas", async () => {
    sent = [];
    server.use(
      http.get("/api/v1/admin/audit-events", async ({ request }) => {
        await record(request);
        return HttpResponse.json(page([EVENT]));
      }),
    );
    renderAt("/admin/auditoria");
    const user = userEvent.setup();

    const table = await screen.findByRole("table", { name: "Eventos de auditoría" });
    const row = within(table).getAllByRole("row")[1];
    expect(row).toHaveTextContent("setting.changed");
    expect(row).toHaveTextContent("teacher_max_access_days");

    await user.type(screen.getByRole("textbox", { name: "Acción" }), "user.disabled");
    await user.type(screen.getByLabelText("Desde"), "2026-10-01");
    await user.click(screen.getByRole("button", { name: "Filtrar" }));

    await vi.waitFor(() => {
      const query = new URLSearchParams(sent.at(-1)?.query);
      expect(query.get("action")).toBe("user.disabled");
      expect(query.get("from")).toBe("2026-10-01T00:00:00-05:00");
    });
  });
});
