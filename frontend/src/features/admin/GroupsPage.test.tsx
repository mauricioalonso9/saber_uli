/**
 * T142: grupos (FR-027; escenarios 6.5 y 6.6).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { AdminUser, Group, GroupMember } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import { page, problemResponse, renderAt } from "@/features/admin/testing";

const GROUP: Group = {
  id: "0192f3c4-0000-7000-8000-0000000000f1",
  name: "Derecho 2026-2",
  cohort_label: "2026-2",
  member_count: 1,
  teachers: [{ id: "0192f3c4-0000-7000-8000-0000000000e9", display_name: "Docente Ruiz" }],
  created_at: "2026-10-01T15:00:00Z",
};

const ANA: GroupMember = {
  user_id: "0192f3c4-0000-7000-8000-0000000000e1",
  display_name: "Ana Pérez",
  email: "ana.perez@unilibre.edu.co",
};

const PEDRO: AdminUser = {
  id: "0192f3c4-0000-7000-8000-0000000000e2",
  kind: "institutional",
  status: "active",
  display_name: "Pedro Gómez",
  email: "pedro.gomez@unilibre.edu.co",
  roles: ["student"],
  director_programs: [],
  created_at: "2026-10-01T15:00:00Z",
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let calls: { method: string; path: string; body?: unknown; query?: string }[];

function mockApi() {
  calls = [];
  const record = async (request: Request) => {
    const url = new URL(request.url);
    const body =
      request.method === "GET" || request.method === "DELETE" ? undefined : await request.json();
    calls.push({ method: request.method, path: url.pathname, body, query: url.search });
  };
  server.use(
    http.get("/api/v1/admin/groups", () => HttpResponse.json(page([GROUP]))),
    http.post("/api/v1/admin/groups", async ({ request }) => {
      await record(request);
      return HttpResponse.json(
        { ...GROUP, id: "nuevo", member_count: 0, teachers: [] },
        {
          status: 201,
        },
      );
    }),
    http.get("/api/v1/admin/groups/:id", () => HttpResponse.json(GROUP)),
    http.patch("/api/v1/admin/groups/:id", async ({ request }) => {
      await record(request);
      return HttpResponse.json({ ...GROUP, archived_at: "2026-10-07T16:00:00Z" });
    }),
    http.get("/api/v1/admin/groups/:id/members", () => HttpResponse.json(page([ANA]))),
    http.post("/api/v1/admin/groups/:id/members", async ({ request }) => {
      await record(request);
      return HttpResponse.json({ ...GROUP, member_count: 2 });
    }),
    http.delete("/api/v1/admin/groups/:id/members/:userId", async ({ request }) => {
      await record(request);
      return new HttpResponse(null, { status: 204 });
    }),
    http.get("/api/v1/admin/users", async ({ request }) => {
      await record(request);
      return HttpResponse.json(page([PEDRO]));
    }),
  );
}

describe("grupos", () => {
  it("lista los grupos y crea uno nuevo", async () => {
    mockApi();
    renderAt("/admin/grupos");
    const user = userEvent.setup();

    const table = await screen.findByRole("table", { name: "Grupos" });
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("Derecho 2026-2");
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("1");
    const form = screen.getByRole("form", { name: "Crear un grupo" });
    await user.type(within(form).getByRole("textbox", { name: "Nombre" }), "Derecho 2027-1");
    await user.type(within(form).getByRole("textbox", { name: /cohorte/i }), "2027-1");
    await user.click(within(form).getByRole("button", { name: "Crear grupo" }));

    expect(await screen.findByText(/creamos el grupo derecho 2027-1/i)).toBeInTheDocument();
    expect(calls).toContainEqual(
      expect.objectContaining({
        method: "POST",
        path: "/api/v1/admin/groups",
        body: { name: "Derecho 2027-1", cohort_label: "2027-1" },
      }),
    );
  });

  it("el detalle muestra miembros y docentes y permite quitar un miembro", async () => {
    mockApi();
    renderAt(`/admin/grupos/${GROUP.id}`);
    const user = userEvent.setup();

    const members = await screen.findByRole("region", { name: "Estudiantes" });
    expect(await within(members).findByText("ana.perez@unilibre.edu.co")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Docentes" })).toHaveTextContent("Docente Ruiz");

    await user.click(within(members).getByRole("button", { name: "Quitar a Ana Pérez" }));

    await vi.waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "DELETE",
          path: `/api/v1/admin/groups/${GROUP.id}/members/${ANA.user_id}`,
        }),
      ),
    );
  });

  it("busca estudiantes y los agrega", async () => {
    mockApi();
    renderAt(`/admin/grupos/${GROUP.id}`);
    const user = userEvent.setup();
    const members = await screen.findByRole("region", { name: "Estudiantes" });

    await user.type(
      within(members).getByRole("searchbox", { name: /buscar estudiantes/i }),
      "pedro",
    );
    await user.click(within(members).getByRole("button", { name: "Buscar" }));
    await user.click(await within(members).findByRole("button", { name: "Agregar a Pedro Gómez" }));

    await vi.waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          method: "POST",
          path: `/api/v1/admin/groups/${GROUP.id}/members`,
          body: { user_ids: [PEDRO.id] },
        }),
      ),
    );
    const search = calls.find((call) => call.path === "/api/v1/admin/users");
    expect(search?.query).toContain("role=student");
    expect(search?.query).toContain("q=pedro");
  });

  it("explica por qué no se agrega a alguien", async () => {
    mockApi();
    const { body, init } = problemResponse(409, "not-institutional-student");
    server.use(http.post("/api/v1/admin/groups/:id/members", () => HttpResponse.json(body, init)));
    renderAt(`/admin/grupos/${GROUP.id}`);
    const user = userEvent.setup();
    const members = await screen.findByRole("region", { name: "Estudiantes" });

    await user.type(within(members).getByRole("searchbox", { name: /buscar estudiantes/i }), "p");
    await user.click(within(members).getByRole("button", { name: "Buscar" }));
    await user.click(await within(members).findByRole("button", { name: "Agregar a Pedro Gómez" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /estudiantes con cuenta institucional/i,
    );
  });

  it("archiva el grupo", async () => {
    mockApi();
    renderAt(`/admin/grupos/${GROUP.id}`);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Archivar el grupo" }));

    await vi.waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({ method: "PATCH", body: { archived: true } }),
      ),
    );
  });
});
