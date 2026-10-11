/**
 * T183: cambio obligatorio de la contraseña de la cuenta local (US9; FR-041, FR-042, FR-045).
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
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

function localMe(pending: boolean): Me {
  return {
    id: "0192f3c4-0000-7000-8000-00000000a001",
    kind: "local",
    status: "active",
    display_name: "Administración Saber Uli",
    email: null,
    roles: ["admin"],
    permissions: pending ? [] : ["users:manage"],
    onboarding: {
      consent_required: false,
      profile_required: false,
      password_change_required: pending,
    },
    access: {
      valid: true,
      validated_at: "2026-10-11T12:00:00Z",
      offline_grace_until: "2026-10-18T12:00:00Z",
    },
  };
}

let requests: unknown[];

function renderPage(path = "/inicio") {
  requests = [];
  let pending = true;
  server.use(
    http.post("/api/auth/local/password", async ({ request }) => {
      const body = (await request.json()) as { new_password: string };
      requests.push(body);
      if (body.new_password === "password1234") {
        return HttpResponse.json(
          {
            type: "urn:saber-uli:problem:weak-password",
            title: "Contraseña débil",
            detail: "Esa contraseña es demasiado común; elige otra.",
          },
          { status: 422 },
        );
      }
      pending = false;
      return HttpResponse.json({ access_token: "nuevo", token_type: "Bearer", expires_in: 600 });
    }),
  );
  useSessionStore.getState().setSession("tok", 600);
  const router = createAppRouter({
    initialPath: path,
    getSession: createSessionLoader(() =>
      Promise.resolve({ kind: "authenticated" as const, me: localMe(pending) }),
    ),
  });
  const view = render(<App router={router} />);
  return { router, container: view.container };
}

async function submit(
  user: ReturnType<typeof userEvent.setup>,
  current: string,
  next: string,
  repeat = next,
) {
  await user.type(screen.getByLabelText("Contraseña actual"), current);
  await user.type(screen.getByLabelText("Contraseña nueva"), next);
  await user.type(screen.getByLabelText("Repite la contraseña nueva"), repeat);
  await user.click(screen.getByRole("button", { name: "Cambiar la contraseña" }));
}

describe("cambio obligatorio de la contraseña", () => {
  it("con el cambio pendiente, cualquier ruta lleva a cambiar la contraseña", async () => {
    const { router } = renderPage("/admin/usuarios");

    expect(
      await screen.findByRole("heading", { level: 1, name: "Cambia la contraseña" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/cambiar-contrasena");
    expect(screen.getByText(/al menos 12 caracteres/)).toBeInTheDocument();
  });

  it("valida en el navegador sin enviar nada", async () => {
    renderPage("/cambiar-contrasena");
    const user = userEvent.setup();
    await screen.findByRole("heading", { level: 1, name: "Cambia la contraseña" });

    await submit(user, "adminsaber", "frase larga y propia", "otra frase distinta");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Las contraseñas nuevas no coinciden.",
    );
    await user.clear(screen.getByLabelText("Contraseña nueva"));
    await user.clear(screen.getByLabelText("Repite la contraseña nueva"));
    await user.type(screen.getByLabelText("Contraseña nueva"), "corta");
    await user.type(screen.getByLabelText("Repite la contraseña nueva"), "corta");
    await user.click(screen.getByRole("button", { name: "Cambiar la contraseña" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("al menos 12 caracteres");
    expect(requests).toEqual([]);
  });

  it("muestra el rechazo del servidor y, al cambiarla, sigue con la sesión nueva", async () => {
    const { router } = renderPage("/cambiar-contrasena");
    const user = userEvent.setup();
    await screen.findByRole("heading", { level: 1, name: "Cambia la contraseña" });

    await submit(user, "adminsaber", "password1234");
    expect(await screen.findByRole("alert")).toHaveTextContent("demasiado común");
    await user.clear(screen.getByLabelText("Contraseña actual"));
    await user.clear(screen.getByLabelText("Contraseña nueva"));
    await user.clear(screen.getByLabelText("Repite la contraseña nueva"));
    await submit(user, "adminsaber", "una frase larga y propia");

    await expect.poll(() => useSessionStore.getState().accessToken).toBe("nuevo");
    await expect.poll(() => router.state.location.pathname).toBe("/inicio");
    expect(requests.at(-1)).toEqual({
      current_password: "adminsaber",
      new_password: "una frase larga y propia",
    });
  });

  it("no tiene violaciones de axe", async () => {
    const { container } = renderPage("/cambiar-contrasena");
    await screen.findByRole("heading", { level: 1, name: "Cambia la contraseña" });

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });

    expect(result.violations).toEqual([]);
  });
});
