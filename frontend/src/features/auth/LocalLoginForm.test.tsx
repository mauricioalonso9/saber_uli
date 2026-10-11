/**
 * T183: ingreso con usuario y contraseña de la cuenta local de administración (US9; FR-040,
 * FR-044).
 */
import "fake-indexeddb/auto";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import type { Me } from "@/api/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { useSessionStore } from "@/features/auth/session-store";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const PROBLEM = "urn:saber-uli:problem:";

const LOCAL_ME: Me = {
  id: "0192f3c4-0000-7000-8000-00000000a001",
  kind: "local",
  status: "active",
  display_name: "Administración Saber Uli",
  email: null,
  roles: ["admin"],
  permissions: [],
  onboarding: { consent_required: false, profile_required: false, password_change_required: true },
  access: {
    valid: true,
    validated_at: "2026-10-11T12:00:00Z",
    offline_grace_until: "2026-10-18T12:00:00Z",
  },
};

function renderLogin() {
  const router = createAppRouter({
    initialPath: "/ingresar",
    getSession: () =>
      Promise.resolve(
        useSessionStore.getState().accessToken
          ? { kind: "authenticated" as const, me: LOCAL_ME }
          : { kind: "anonymous" as const },
      ),
  });
  const view = render(<App router={router} />);
  return { router, container: view.container };
}

async function fill(user: ReturnType<typeof userEvent.setup>, password: string) {
  await user.click(await screen.findByRole("button", { name: "Ingreso de administración" }));
  await user.type(screen.getByLabelText("Usuario"), "adminsaber");
  await user.type(screen.getByLabelText("Contraseña"), password);
  await user.click(screen.getByRole("button", { name: "Ingresar con usuario y contraseña" }));
}

describe("ingreso de la cuenta local", () => {
  it("guarda la sesión y sigue", async () => {
    let body: unknown = null;
    server.use(
      http.post("/api/auth/local/sessions", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ access_token: "tok", token_type: "Bearer", expires_in: 600 });
      }),
    );
    const { router } = renderLogin();
    const user = userEvent.setup();

    await fill(user, "adminsaber");

    await expect.poll(() => useSessionStore.getState().accessToken).toBe("tok");
    expect(body).toEqual({ username: "adminsaber", password: "adminsaber" });
    // Con el cambio pendiente, la guarda lleva a cambiar la contraseña (FR-041).
    await expect.poll(() => router.state.location.pathname).toBe("/cambiar-contrasena");
  });

  it("muestra el mensaje genérico de credenciales incorrectas", async () => {
    server.use(
      http.post("/api/auth/local/sessions", () =>
        HttpResponse.json(
          {
            type: `${PROBLEM}invalid-credentials`,
            title: "Credenciales incorrectas",
            detail: "El usuario o la contraseña no son correctos.",
          },
          { status: 401 },
        ),
      ),
    );
    renderLogin();
    const user = userEvent.setup();

    await fill(user, "mala");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El usuario o la contraseña no son correctos.",
    );
    expect(useSessionStore.getState().accessToken).toBeNull();
  });

  it("explica el bloqueo temporal", async () => {
    server.use(
      http.post("/api/auth/local/sessions", () =>
        HttpResponse.json(
          {
            type: `${PROBLEM}account-locked`,
            title: "Cuenta bloqueada",
            detail: "Demasiados intentos fallidos. Intenta de nuevo en 15 minutos.",
          },
          { status: 429, headers: { "Retry-After": "900" } },
        ),
      ),
    );
    renderLogin();
    const user = userEvent.setup();

    await fill(user, "mala");

    expect(await screen.findByRole("alert")).toHaveTextContent("Intenta de nuevo en 15 minutos.");
  });

  it("no tiene violaciones de axe con el formulario abierto", async () => {
    const { container } = renderLogin();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Ingreso de administración" }));

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });

    expect(result.violations).toEqual([]);
  });
});
