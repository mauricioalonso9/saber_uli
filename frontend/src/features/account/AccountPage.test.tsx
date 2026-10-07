/**
 * T101: editar el perfil desde `/mi-cuenta` (FR-021; escenario 3.4).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Me, Profile, ProfileUpdate, Program } from "@/api/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const DERECHO: Program = {
  id: "0192f3c4-0000-7000-8000-0000000000b1",
  code: "DER-BOG",
  name: "Derecho",
  campus: "Bogotá",
  active: true,
};

const PROFILE: Profile = {
  program: DERECHO,
  semester: 8,
  expected_exam_date: "2027-05-30",
  daily_goal: "regular",
  complete: true,
};

const ME: Me = {
  id: "0192f3c4-0000-7000-8000-000000000001",
  kind: "institutional",
  status: "active",
  display_name: "Ana Pérez",
  email: "ana.perez@unilibre.edu.co",
  roles: ["student"],
  permissions: [],
  onboarding: { consent_required: false, profile_required: false },
  access: {
    valid: true,
    validated_at: "2026-10-07T12:00:00Z",
    offline_grace_until: "2026-10-14T12:00:00Z",
  },
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let saved: ProfileUpdate[];

function renderAccount() {
  saved = [];
  server.use(
    http.get("/api/v1/programs", () => HttpResponse.json([DERECHO])),
    http.get("/api/v1/me/profile", () => HttpResponse.json(PROFILE)),
    http.put("/api/v1/me/profile", async ({ request }) => {
      const body = (await request.json()) as ProfileUpdate;
      saved.push(body);
      return HttpResponse.json({ ...PROFILE, ...body, complete: true });
    }),
  );
  const router = createAppRouter({
    initialPath: "/mi-cuenta",
    getSession: createSessionLoader(() => Promise.resolve({ kind: "authenticated", me: ME })),
  });
  render(<App router={router} />);
  return router;
}

describe("mi cuenta", () => {
  it("carga el perfil actual en el formulario", async () => {
    renderAccount();

    expect(await screen.findByRole("heading", { name: "Mi cuenta" })).toBeInTheDocument();
    expect(await screen.findByRole("combobox", { name: "Semestre" })).toHaveValue("8");
    expect(screen.getByRole("combobox", { name: "Programa académico" })).toHaveValue(DERECHO.id);
    expect(screen.getByLabelText("Fecha estimada de tu prueba Saber Pro")).toHaveValue(
      "2027-05-30",
    );
    expect(screen.getByRole("radio", { name: /regular/i })).toBeChecked();
  });

  it("guarda los cambios y lo confirma sin salir de la página", async () => {
    const router = renderAccount();
    const user = userEvent.setup();

    await user.selectOptions(await screen.findByRole("combobox", { name: "Semestre" }), "9");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(await screen.findByText("Guardamos tus cambios.")).toHaveAttribute("role", "status");
    expect(router.state.location.pathname).toBe("/mi-cuenta");
    expect(saved[0]).toMatchObject({ program_id: DERECHO.id, semester: 9 });
  });

  it("enlaza la autorización de datos y la sección de mis datos", async () => {
    renderAccount();

    await screen.findByRole("heading", { name: "Mi cuenta" });
    const main = screen.getByRole("main");
    expect(within(main).getByRole("link", { name: "Mi autorización de datos" })).toHaveAttribute(
      "href",
      "/mi-cuenta/autorizacion",
    );
    expect(within(main).getByRole("link", { name: "Mis datos" })).toHaveAttribute(
      "href",
      "/mi-cuenta/datos",
    );
  });
});
