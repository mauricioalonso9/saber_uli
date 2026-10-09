/**
 * T142: administración de cuentas (FR-023 a FR-026, FR-029; escenarios 6.1 a 6.4).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { AdminUser, Program } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import { page, problemResponse, renderAt } from "@/features/admin/testing";

const DERECHO: Program = {
  id: "0192f3c4-0000-7000-8000-0000000000b1",
  code: "DER-BOG",
  name: "Derecho",
  campus: "Bogotá",
  active: true,
};

function account(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    id: "0192f3c4-0000-7000-8000-0000000000e1",
    kind: "institutional",
    status: "active",
    display_name: "Ana Pérez",
    email: "ana.perez@unilibre.edu.co",
    roles: ["student", "teacher"],
    director_programs: [],
    created_at: "2026-10-01T15:00:00Z",
    ...overrides,
  };
}

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let queries: URLSearchParams[];
let roleUpdates: unknown[];
let statusUpdates: unknown[];
let current: AdminUser;

function mockApi() {
  queries = [];
  roleUpdates = [];
  statusUpdates = [];
  current = account();
  server.use(
    http.get("/api/v1/admin/users", ({ request }) => {
      queries.push(new URL(request.url).searchParams);
      return HttpResponse.json(page([current]));
    }),
    http.get("/api/v1/admin/programs", () => HttpResponse.json(page([DERECHO]))),
    http.put("/api/v1/admin/users/:id/roles", async ({ request }) => {
      const body = (await request.json()) as { roles: AdminUser["roles"] };
      roleUpdates.push(body);
      current = { ...current, roles: body.roles, director_programs: [DERECHO] };
      return HttpResponse.json(current);
    }),
    http.patch("/api/v1/admin/users/:id", async ({ request }) => {
      const body = (await request.json()) as { status: AdminUser["status"] };
      statusUpdates.push(body);
      current = { ...current, status: body.status };
      return HttpResponse.json(current);
    }),
  );
}

async function accountsTable() {
  return screen.findByRole("table", { name: "Cuentas" });
}

describe("cuentas", () => {
  it("lista las cuentas con sus roles y estado", async () => {
    mockApi();
    renderAt("/admin/usuarios");

    const [row] = within(await accountsTable())
      .getAllByRole("row")
      .slice(1);
    expect(row).toHaveTextContent("Ana Pérez");
    expect(row).toHaveTextContent("ana.perez@unilibre.edu.co");
    expect(row).toHaveTextContent("Estudiante, Docente");
    expect(row).toHaveTextContent("Activa");
  });

  it("busca y filtra por rol", async () => {
    mockApi();
    renderAt("/admin/usuarios");
    const user = userEvent.setup();

    await user.type(await screen.findByRole("searchbox", { name: /buscar/i }), "ana");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Rol" }), "Docente");

    await vi.waitFor(() => {
      expect(queries.at(-1)?.get("q")).toBe("ana");
      expect(queries.at(-1)?.get("role")).toBe("teacher");
    });
  });

  it("edita los roles y los programas del director", async () => {
    mockApi();
    renderAt("/admin/usuarios");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Editar roles de Ana Pérez" }));
    const editor = screen.getByRole("group", { name: "Roles de Ana Pérez" });
    const student = within(editor).getByRole("checkbox", { name: "Estudiante" });
    expect(student).toBeChecked();
    expect(student).toBeDisabled();
    await user.click(within(editor).getByRole("checkbox", { name: "Docente" }));
    await user.click(within(editor).getByRole("checkbox", { name: "Director de programa" }));
    await user.click(await within(editor).findByRole("checkbox", { name: "Derecho (Bogotá)" }));
    await user.click(within(editor).getByRole("button", { name: "Guardar roles" }));

    expect(await screen.findByText(/actualizamos los roles de ana pérez/i)).toBeInTheDocument();
    expect(roleUpdates).toEqual([
      { roles: ["student", "program_director"], director_program_ids: [DERECHO.id] },
    ]);
  });

  it("explica la regla del último administrador", async () => {
    mockApi();
    const { body, init } = problemResponse(
      409,
      "last-admin",
      "No puedes quitar el rol Administrador al último administrador activo.",
    );
    server.use(http.put("/api/v1/admin/users/:id/roles", () => HttpResponse.json(body, init)));
    renderAt("/admin/usuarios");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Editar roles de Ana Pérez" }));
    await user.click(screen.getByRole("button", { name: "Guardar roles" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/último administrador activo/i);
  });

  it("desactiva con confirmación y luego permite reactivar", async () => {
    mockApi();
    renderAt("/admin/usuarios");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Desactivar a Ana Pérez" }));
    const dialog = screen.getByRole("alertdialog", { name: /desactivar a ana pérez/i });
    await user.click(within(dialog).getByRole("button", { name: "Sí, desactivar" }));

    expect(
      await screen.findByRole("button", { name: "Reactivar a Ana Pérez" }),
    ).toBeInTheDocument();
    expect(within(await accountsTable()).getAllByRole("row")[1]).toHaveTextContent("Desactivada");
    expect(statusUpdates).toEqual([{ status: "disabled" }]);
  });
});
