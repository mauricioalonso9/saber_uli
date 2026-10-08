/**
 * T157: solicitar la supresión de la cuenta desde `/mi-cuenta` (FR-032; escenarios 7.1, 7.2 y
 * 7.5).
 */
import "fake-indexeddb/auto";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { DeletionRequest, Me, Profile, Program } from "@/api/model";
import { App } from "@/app/App";
import type { SessionState } from "@/app/guards";
import { createAppRouter } from "@/app/router";
import { evaluateOfflineAccess, saveValidation } from "@/features/auth/offline-access";
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

const REQUEST: DeletionRequest = {
  id: "0192f3c4-0000-7000-8000-0000000000e1",
  status: "received",
  origin: "user_request",
  requested_at: "2026-10-06T17:00:00Z",
  due_date: "2026-10-28",
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let sent: unknown[];

function renderAccount(reply?: () => Response) {
  sent = [];
  let session: SessionState = { kind: "authenticated", me: ME };
  server.use(
    http.get("/api/v1/programs", () => HttpResponse.json([DERECHO])),
    http.get("/api/v1/me/profile", () => HttpResponse.json(PROFILE)),
    http.post("/api/v1/me/deletion-request", async ({ request }) => {
      sent.push(await request.json());
      if (reply) return reply();
      session = { kind: "anonymous" };
      return HttpResponse.json(REQUEST, { status: 202 });
    }),
  );
  const router = createAppRouter({
    initialPath: "/mi-cuenta",
    getSession: createSessionLoader(() => Promise.resolve(session)),
  });
  render(<App router={router} />);
  return router;
}

async function openConfirmation() {
  const user = userEvent.setup();
  const section = await screen.findByRole("region", { name: "Eliminar mi cuenta" });
  await user.click(within(section).getByRole("button", { name: "Eliminar mi cuenta" }));
  const dialog = screen.getByRole("alertdialog", { name: /eliminar tu cuenta/i });
  return { user, section, dialog };
}

describe("eliminar mi cuenta", () => {
  it("explica qué se borra, qué se conserva sin identificarte y que es irreversible", async () => {
    renderAccount();

    const section = await screen.findByRole("region", { name: "Eliminar mi cuenta" });
    expect(section).toHaveTextContent(/nombre, correo, perfil/i);
    expect(section).toHaveTextContent(/se conservan sin datos que te identifiquen/i);
    expect(section).toHaveTextContent(/no se puede deshacer/i);
    expect(section).toHaveTextContent(/15 días hábiles/i);
    expect(section).toHaveTextContent(/cuenta nueva/i);
  });

  it("exige escribir ELIMINAR antes de confirmar", async () => {
    renderAccount();
    const { user, dialog } = await openConfirmation();
    const confirm = within(dialog).getByRole("button", { name: "Eliminar definitivamente" });
    const input = within(dialog).getByRole("textbox", { name: /escribe ELIMINAR/i });

    expect(confirm).toBeDisabled();
    await user.type(input, "eliminar");
    expect(confirm).toBeDisabled();
    await user.clear(input);
    await user.type(input, "ELIMINAR");
    expect(confirm).toBeEnabled();
  });

  it("cancelar no envía la solicitud", async () => {
    renderAccount();
    const { user, dialog } = await openConfirmation();

    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(sent).toHaveLength(0);
  });

  it("al confirmar cierra la sesión y muestra la fecha límite (escenario 7.2)", async () => {
    await saveValidation(ME, new Date());
    renderAccount();
    const { user, dialog } = await openConfirmation();

    await user.type(within(dialog).getByRole("textbox", { name: /escribe ELIMINAR/i }), "ELIMINAR");
    await user.click(within(dialog).getByRole("button", { name: "Eliminar definitivamente" }));

    const done = await screen.findByRole("status", { name: /solicitamos la supresión/i });
    expect(done).toHaveTextContent(/28 de octubre de 2026/i);
    expect(sent).toEqual([{ confirmation: "ELIMINAR" }]);
    expect(useSessionStore.getState().accessToken).toBeNull();
    expect((await evaluateOfflineAccess()).status).toBe("none");
  });

  it("el último administrador recibe la explicación (escenario 7.5)", async () => {
    renderAccount(() =>
      HttpResponse.json(
        {
          type: "urn:saber-uli:problem:last-admin",
          title: "Conflicto",
          status: 409,
          detail: "Asigna el rol Administrador a otra persona antes de eliminar tu cuenta.",
        },
        { status: 409, headers: { "Content-Type": "application/problem+json" } },
      ),
    );
    const { user, dialog } = await openConfirmation();

    await user.type(within(dialog).getByRole("textbox", { name: /escribe ELIMINAR/i }), "ELIMINAR");
    await user.click(within(dialog).getByRole("button", { name: "Eliminar definitivamente" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/rol Administrador a otra persona/);
    expect(useSessionStore.getState().accessToken).toBe("token");
  });
});
