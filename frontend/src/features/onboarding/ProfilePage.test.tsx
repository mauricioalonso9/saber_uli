/**
 * T097: perfil del primer ingreso (FR-019 a FR-022; escenarios 3.1 a 3.3).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Me, Profile, ProfileUpdate, Program } from "@/api/model";
import { App } from "@/app/App";
import type { SessionState } from "@/app/guards";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const PROGRAMS: Program[] = [
  {
    id: "0192f3c4-0000-7000-8000-0000000000b1",
    code: "DER-BOG",
    name: "Derecho",
    campus: "Bogotá",
    active: true,
  },
  {
    id: "0192f3c4-0000-7000-8000-0000000000b2",
    code: "CON-CAL",
    name: "Contaduría Pública",
    campus: "Cali",
    active: true,
  },
];

function me(kind: Me["kind"]): Me {
  return {
    id: "0192f3c4-0000-7000-8000-000000000001",
    kind,
    status: "active",
    display_name: kind === "guest" ? "" : "Ana Pérez",
    email: kind === "guest" ? "laura@correo.co" : "ana.perez@unilibre.edu.co",
    roles: [kind === "guest" ? "guest" : "student"],
    permissions: [],
    onboarding: { consent_required: false, profile_required: true },
    access: {
      valid: true,
      validated_at: "2026-10-07T12:00:00Z",
      offline_grace_until: "2026-10-14T12:00:00Z",
    },
  };
}

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let saved: ProfileUpdate[];

function renderProfile(kind: Me["kind"]) {
  saved = [];
  let session: SessionState = { kind: "authenticated", me: me(kind) };
  server.use(
    http.get("/api/v1/programs", () => HttpResponse.json(PROGRAMS)),
    http.get("/api/v1/me/profile", () =>
      HttpResponse.json({ daily_goal: "regular", complete: false } satisfies Profile),
    ),
    http.put("/api/v1/me/profile", async ({ request }) => {
      const body = (await request.json()) as ProfileUpdate;
      saved.push(body);
      session = {
        kind: "authenticated",
        me: { ...me(kind), onboarding: { consent_required: false, profile_required: false } },
      };
      return HttpResponse.json({ ...body, complete: true });
    }),
  );
  const router = createAppRouter({
    initialPath: "/bienvenida/perfil",
    getSession: createSessionLoader(() => Promise.resolve(session)),
  });
  render(<App router={router} />);
  return router;
}

describe("perfil del primer ingreso: institucional", () => {
  it("muestra nombre y correo del directorio sin poder editarlos (FR-021)", async () => {
    renderProfile("institutional");

    const directory = await screen.findByRole("region", { name: /datos de tu cuenta unilibre/i });
    expect(directory).toHaveTextContent("Ana Pérez");
    expect(directory).toHaveTextContent("ana.perez@unilibre.edu.co");
    expect(within(directory).queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("pide solo programa, semestre, fecha de la prueba y meta diaria (FR-019)", async () => {
    renderProfile("institutional");

    const form = await screen.findByRole("form", { name: /completa tu perfil/i });
    expect(within(form).getByRole("combobox", { name: "Programa académico" })).toBeInTheDocument();
    expect(within(form).getByRole("combobox", { name: "Semestre" })).toBeInTheDocument();
    expect(within(form).getByLabelText("Fecha estimada de tu prueba Saber Pro")).toHaveAttribute(
      "type",
      "date",
    );
    expect(within(form).getByRole("radiogroup", { name: "Meta diaria" })).toBeInTheDocument();
    expect(within(form).queryByLabelText(/tu nombre/i)).not.toBeInTheDocument();
    expect(within(form).getAllByRole("radio")).toHaveLength(3);
  });

  it("guarda el perfil y continúa al inicio", async () => {
    const router = renderProfile("institutional");
    const user = userEvent.setup();

    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Programa académico" }),
      "Contaduría Pública (Cali)",
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "Semestre" }), "8");
    await user.type(screen.getByLabelText("Fecha estimada de tu prueba Saber Pro"), "2027-05-30");
    await user.click(screen.getByRole("radio", { name: /intensa/i }));
    await user.click(screen.getByRole("button", { name: "Guardar y continuar" }));

    expect(await screen.findByRole("heading", { name: "Inicio" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/inicio");
    expect(saved).toEqual([
      {
        program_id: PROGRAMS[1]?.id,
        semester: 8,
        expected_exam_date: "2027-05-30",
        daily_goal: "intense",
      },
    ]);
  });

  it("marca los errores en cada campo de forma accesible y no envía nada", async () => {
    renderProfile("institutional");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Guardar y continuar" }));

    for (const field of [
      screen.getByRole("combobox", { name: "Programa académico" }),
      screen.getByRole("combobox", { name: "Semestre" }),
      screen.getByLabelText("Fecha estimada de tu prueba Saber Pro"),
    ]) {
      expect(field).toHaveAttribute("aria-invalid", "true");
      expect(field).toHaveAccessibleDescription(/elige|indica/i);
    }
    expect(screen.getByRole("combobox", { name: "Programa académico" })).toHaveFocus();
    expect(saved).toEqual([]);
  });

  it("muestra el error del servidor", async () => {
    renderProfile("institutional");
    server.use(
      http.put("/api/v1/me/profile", () =>
        HttpResponse.json(
          { type: "urn:saber-uli:problem:program-not-available", title: "Error", status: 422 },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const user = userEvent.setup();

    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Programa académico" }),
      "Derecho (Bogotá)",
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "Semestre" }), "3");
    await user.type(screen.getByLabelText("Fecha estimada de tu prueba Saber Pro"), "2027-05-30");
    await user.click(screen.getByRole("button", { name: "Guardar y continuar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/programa.*no está disponible/i);
  });
});

describe("perfil del primer ingreso: invitado", () => {
  it("pide nombre, meta y fecha opcional, sin programa ni semestre (FR-020)", async () => {
    renderProfile("guest");

    const form = await screen.findByRole("form", { name: /completa tu perfil/i });
    expect(within(form).getByRole("textbox", { name: "Tu nombre" })).toBeInTheDocument();
    expect(within(form).getByRole("radiogroup", { name: "Meta diaria" })).toBeInTheDocument();
    expect(
      within(form).getByLabelText("Fecha estimada de tu prueba Saber Pro (opcional)"),
    ).toBeInTheDocument();
    expect(within(form).queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("guarda solo nombre y meta cuando no indica fecha", async () => {
    const router = renderProfile("guest");
    const user = userEvent.setup();

    await user.type(await screen.findByRole("textbox", { name: "Tu nombre" }), "Laura Gómez");
    await user.click(screen.getByRole("button", { name: "Guardar y continuar" }));

    expect(await screen.findByRole("heading", { name: "Inicio" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/inicio");
    expect(saved).toEqual([{ guest_display_name: "Laura Gómez", daily_goal: "regular" }]);
  });

  it("valida la longitud del nombre", async () => {
    renderProfile("guest");
    const user = userEvent.setup();

    await user.type(await screen.findByRole("textbox", { name: "Tu nombre" }), "L");
    await user.click(screen.getByRole("button", { name: "Guardar y continuar" }));

    const name = screen.getByRole("textbox", { name: "Tu nombre" });
    expect(name).toHaveAttribute("aria-invalid", "true");
    expect(name).toHaveAccessibleDescription(/entre 2 y 120 caracteres/i);
    expect(saved).toEqual([]);
  });
});
