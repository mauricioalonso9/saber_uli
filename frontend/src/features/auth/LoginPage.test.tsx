/**
 * T075: página de ingreso (FR-001, FR-002, SC-008) y cierre de sesión (escenario 1.4).
 */
import "fake-indexeddb/auto";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Me } from "@/api/model";
import { App } from "@/app/App";
import type { SessionState } from "@/app/guards";
import { createAppRouter } from "@/app/router";
import { browser } from "@/features/auth/bootstrap";
import { evaluateOfflineAccess, saveValidation } from "@/features/auth/offline-access";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
});
afterAll(() => server.close());

const ME: Me = {
  id: "0192f3c4-0000-7000-8000-000000000001",
  kind: "institutional",
  status: "active",
  display_name: "Ana",
  email: "ana@unilibre.edu.co",
  roles: ["student"],
  permissions: [],
  onboarding: { consent_required: false, profile_required: false },
  access: {
    valid: true,
    validated_at: "2026-10-07T12:00:00Z",
    offline_grace_until: "2026-10-14T12:00:00Z",
  },
};

function renderLogin(search = "") {
  const router = createAppRouter({
    initialPath: `/ingresar${search}`,
    getSession: () => Promise.resolve({ kind: "anonymous" }),
  });
  render(<App router={router} />);
  return router;
}

describe("página de ingreso", () => {
  it("ofrece ingresar con la cuenta Unilibre y lleva al inicio del flujo", async () => {
    const assign = vi.spyOn(browser, "assign").mockImplementation(() => undefined);
    const user = userEvent.setup();
    renderLogin("?return_to=%2Fmi-cuenta");

    await user.click(
      await screen.findByRole("button", { name: "Ingresar con mi cuenta Unilibre" }),
    );

    expect(assign).toHaveBeenCalledWith("/api/auth/microsoft/login?return_to=%2Fmi-cuenta");
  });

  it("sin return_to inicia el flujo sin parámetro", async () => {
    const assign = vi.spyOn(browser, "assign").mockImplementation(() => undefined);
    const user = userEvent.setup();
    renderLogin();

    await user.click(
      await screen.findByRole("button", { name: "Ingresar con mi cuenta Unilibre" }),
    );

    expect(assign).toHaveBeenCalledWith("/api/auth/microsoft/login");
  });

  it("explica el rechazo de una cuenta externa y la alternativa de invitación (SC-008)", async () => {
    renderLogin("?error=tenant_not_allowed");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/no pertenece a la Universidad Libre/i);
    expect(alert).toHaveTextContent(/invitación/i);
  });

  it("explica cuando Microsoft no está disponible", async () => {
    renderLogin("?error=idp_unavailable");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /no pudimos conectar con Microsoft/i,
    );
  });

  it.each([
    ["account_disabled", /desactivada/i],
    ["login_cancelled", /cancelaste/i],
    ["invalid_state", /vuelve a intentarlo/i],
    ["codigo_desconocido", /no pudimos completar el ingreso/i],
  ])("muestra un mensaje para %s", async (code, message) => {
    renderLogin(`?error=${code}`);

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("sin error no muestra alertas", async () => {
    renderLogin();

    await screen.findByRole("button", { name: "Ingresar con mi cuenta Unilibre" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("enlaza el ingreso de invitados", async () => {
    renderLogin();

    const link = await screen.findByRole("link", { name: /soy invitado/i });
    expect(link).toHaveAttribute("href", "/ingresar/invitado");
  });
});

describe("cerrar sesión", () => {
  it("revoca la sesión, borra el token y la instantánea, y vuelve a /ingresar", async () => {
    const logoutCalls: Request[] = [];
    server.use(
      http.post("/api/auth/logout", ({ request }) => {
        logoutCalls.push(request.clone());
        return new HttpResponse(null, { status: 204 });
      }),
    );
    useSessionStore.getState().setSession("token", 600);
    await saveValidation(ME, new Date());
    let session: SessionState = { kind: "authenticated", me: ME };
    const getSession = createSessionLoader(() => Promise.resolve(session));
    const router = createAppRouter({ initialPath: "/inicio", getSession });
    const user = userEvent.setup();
    render(<App router={router} />);

    const banner = await screen.findByRole("banner");
    session = { kind: "anonymous" };
    await user.click(within(banner).getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "Ingresar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/ingresar");
    expect(logoutCalls).toHaveLength(1);
    expect(logoutCalls[0]?.headers.get("X-Requested-With")).toBe("saber-uli");
    expect(useSessionStore.getState().accessToken).toBeNull();
    expect((await evaluateOfflineAccess()).status).toBe("none");
  });

  it("sin sesión no muestra el botón de cerrar sesión", async () => {
    renderLogin();

    await screen.findByRole("button", { name: "Ingresar con mi cuenta Unilibre" });
    expect(screen.queryByRole("button", { name: "Cerrar sesión" })).not.toBeInTheDocument();
  });
});
