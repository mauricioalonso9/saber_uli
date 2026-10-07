/**
 * Fin de la sesión por una causa definitiva (FR-010, FR-011; escenario 5.4; SC-003): si la
 * renovación responde que el acceso del invitado fue revocado o venció, o que la cuenta está
 * desactivada o eliminada, la app vuelve a `/ingresar` y explica la causa en la siguiente acción.
 */
import "fake-indexeddb/auto";

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

const GUEST: Me = {
  id: "0192f3c4-0000-7000-8000-000000000009",
  kind: "guest",
  status: "active",
  display_name: "Laura",
  email: "laura@correo.co",
  roles: ["guest"],
  permissions: [],
  onboarding: { consent_required: false, profile_required: false },
  access: {
    valid: true,
    validated_at: "2026-10-07T12:00:00Z",
    offline_grace_until: "2026-10-14T12:00:00Z",
  },
};

function problem(slug: string) {
  return HttpResponse.json(
    { type: `urn:saber-uli:problem:${slug}`, title: "No autenticado", status: 401 },
    { status: 401, headers: { "Content-Type": "application/problem+json" } },
  );
}

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

describe("fin de la sesión por una causa definitiva", () => {
  it.each([
    ["guest-access-revoked", /fue retirado/i],
    ["guest-access-expired", /venció/i],
    ["account-disabled", /desactivada/i],
  ])("con %s vuelve a /ingresar y lo explica", async (slug, message) => {
    useSessionStore.getState().setSession("token-viejo", 600);
    // Como `loadSession`: tras una renovación rechazada, la sesión es anónima.
    let session: SessionState = { kind: "authenticated", me: GUEST };
    server.use(
      // La API rechaza el token (época nueva) y la renovación da la causa.
      http.get("/api/v1/me/profile", () => problem(slug)),
      http.get("/api/v1/programs", () => problem(slug)),
      http.post("/api/auth/refresh", () => {
        session = { kind: "anonymous" };
        return problem(slug);
      }),
    );
    const router = createAppRouter({
      initialPath: "/inicio",
      getSession: createSessionLoader(() => Promise.resolve(session)),
    });
    render(<App router={router} />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("link", { name: "Mi cuenta" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(router.state.location.pathname).toBe("/ingresar");
    expect(useSessionStore.getState().accessToken).toBeNull();
  });
});
