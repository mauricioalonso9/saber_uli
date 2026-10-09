/**
 * T112: ingreso del invitado con el enlace del correo (FR-007, FR-011; research R-18).
 *
 * El token llega en el fragmento (`/acceso#t=…`), se borra del historial al abrir la página y
 * solo se envía al pulsar «Ingresar» (los filtros de correo abren los enlaces con GET).
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import type { Me } from "@/api/model";
import { App } from "@/app/App";
import type { SessionState } from "@/app/guards";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const TOKEN = "Qx7dJ2kq9vX0pY3sT8wR1mN4bH6cF5gL2aZ0eU9iO3u";

const GUEST: Me = {
  id: "0192f3c4-0000-7000-8000-000000000009",
  kind: "guest",
  status: "active",
  display_name: "",
  email: "laura@correo.co",
  roles: ["guest"],
  permissions: [],
  onboarding: { consent_required: true, profile_required: true },
  access: {
    valid: true,
    validated_at: "2026-10-07T12:00:00Z",
    offline_grace_until: "2026-10-14T12:00:00Z",
  },
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let sent: unknown[];

function renderAccess(path = `/acceso#t=${TOKEN}`) {
  sent = [];
  let session: SessionState = { kind: "anonymous" };
  server.use(
    http.post("/api/auth/guest/sessions", async ({ request }) => {
      sent.push(await request.json());
      session = { kind: "authenticated", me: GUEST };
      return HttpResponse.json(
        { access_token: "token-del-invitado", token_type: "Bearer", expires_in: 600 },
        { headers: { "Set-Cookie": "su_refresh=x; Path=/api/auth; HttpOnly" } },
      );
    }),
  );
  const router = createAppRouter({
    initialPath: path,
    getSession: createSessionLoader(() => Promise.resolve(session)),
  });
  render(<App router={router} />);
  return router;
}

function failWith(status: number, slug: string) {
  server.use(
    http.post("/api/auth/guest/sessions", () =>
      HttpResponse.json(
        { type: `urn:saber-uli:problem:${slug}`, title: "Error", status },
        { status, headers: { "Content-Type": "application/problem+json" } },
      ),
    ),
  );
}

describe("acceso del invitado", () => {
  it("borra el token del historial al abrir la página y no envía nada todavía", async () => {
    const router = renderAccess();

    expect(await screen.findByRole("button", { name: "Ingresar" })).toBeInTheDocument();
    expect(router.state.location.href).not.toContain(TOKEN);
    expect(router.history.location.href).not.toContain(TOKEN);
    expect(sent).toEqual([]);
  });

  it("al pulsar Ingresar envía el token, guarda la sesión y sigue al primer ingreso", async () => {
    const router = renderAccess();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Ingresar" }));

    expect(
      await screen.findByRole("heading", { name: "Tratamiento de tus datos" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/bienvenida/datos");
    expect(sent).toEqual([{ token: TOKEN }]);
    expect(useSessionStore.getState().accessToken).toBe("token-del-invitado");
  });

  it.each([
    [400, "access-link-invalid", /no es válido, ya se usó o venció/i],
    [403, "guest-access-expired", /venció/i],
    [403, "guest-access-revoked", /fue retirado/i],
  ])("explica el error %i %s y ofrece pedir un enlace nuevo", async (status, slug, message) => {
    renderAccess();
    failWith(status, slug);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("link", { name: /pedir un enlace nuevo/i })).toHaveAttribute(
      "href",
      "/ingresar/invitado",
    );
    expect(useSessionStore.getState().accessToken).toBeNull();
  });

  it("sin token en el enlace explica cómo entrar", async () => {
    renderAccess("/acceso");

    expect(await screen.findByText(/abre el enlace que te enviamos/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ingresar" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pedir un enlace nuevo/i })).toBeInTheDocument();
  });
});
