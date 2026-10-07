/**
 * T086: consultar y revocar la autorización de datos (FR-018; escenarios 2.4 y 2.5).
 */
import "fake-indexeddb/auto";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Consent, Me, PolicyVersion } from "@/api/model";
import { App } from "@/app/App";
import type { SessionState } from "@/app/guards";
import { createAppRouter } from "@/app/router";
import { evaluateOfflineAccess, saveValidation } from "@/features/auth/offline-access";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const POLICY: PolicyVersion = {
  id: "0192f3c4-0000-7000-8000-0000000000a1",
  version: "1.0",
  title: "Política de tratamiento de datos personales de Saber Uli",
  effective_from: "2026-10-01T05:00:00Z",
  body_markdown: "# Política\n\n## 2. Finalidades\n\nUsamos sus datos para medir su progreso.\n",
};

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

function consent(decision: Consent["decision"], decidedAt: string, id = "c1"): Consent {
  return {
    id: `0192f3c4-0000-7000-8000-0000000000${id}`,
    policy_version_id: POLICY.id,
    policy_version: POLICY.version,
    decision,
    channel: "web_pwa",
    decided_at: decidedAt,
  };
}

const ACCEPTED = consent("accepted", "2026-10-07T15:30:00Z", "c2");
const REJECTED = consent("rejected", "2026-10-06T14:00:00Z", "c1");

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let revocations: number;

function renderSettings() {
  revocations = 0;
  let session: SessionState = { kind: "authenticated", me: ME };
  server.use(
    http.get("/api/v1/me/consents", () =>
      HttpResponse.json({ current: ACCEPTED, items: [ACCEPTED, REJECTED] }),
    ),
    http.get(`/api/v1/privacy-policy/versions/${POLICY.id}`, () => HttpResponse.json(POLICY)),
    http.post("/api/v1/me/consents/revocation", () => {
      revocations += 1;
      session = { kind: "anonymous" };
      return HttpResponse.json(consent("revoked", "2026-10-08T13:00:00Z", "c3"), {
        status: 201,
      });
    }),
  );
  const router = createAppRouter({
    initialPath: "/mi-cuenta/autorizacion",
    getSession: createSessionLoader(() => Promise.resolve(session)),
  });
  render(<App router={router} />);
  return router;
}

describe("mi autorización de datos", () => {
  it("muestra la versión aceptada y la fecha de la aceptación", async () => {
    renderSettings();

    const current = await screen.findByRole("region", { name: /autorización vigente/i });
    expect(current).toHaveTextContent(/versión 1\.0/i);
    expect(current).toHaveTextContent(/7 de octubre de 2026/i);
  });

  it("muestra el historial de decisiones", async () => {
    renderSettings();

    const history = await screen.findByRole("list", { name: /historial/i });
    const items = within(history).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent(/aceptaste/i);
    expect(items[1]).toHaveTextContent(/no aceptaste/i);
  });

  it("permite ver el texto de la versión aceptada", async () => {
    renderSettings();
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: /ver el texto de la versión 1\.0/i }),
    );

    expect(await screen.findByRole("heading", { name: "2. Finalidades" })).toBeInTheDocument();
  });

  it("revocar pide confirmación y cancelar no revoca", async () => {
    renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Revocar mi autorización" }));
    const confirm = screen.getByRole("alertdialog", { name: /revocar tu autorización/i });
    expect(confirm).toHaveTextContent(/no podrás usar saber uli/i);

    await user.click(within(confirm).getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(revocations).toBe(0);
  });

  it("confirmar revoca, borra la sesión local y ofrece ingresar de nuevo (escenario 2.5)", async () => {
    await saveValidation(ME, new Date());
    const router = renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Revocar mi autorización" }));
    await user.click(screen.getByRole("button", { name: "Sí, revocar" }));

    const done = await screen.findByRole("status", { name: /revocaste tu autorización/i });
    expect(done).toHaveTextContent(/solicitar la supresión/i);
    expect(revocations).toBe(1);
    expect(useSessionStore.getState().accessToken).toBeNull();
    expect((await evaluateOfflineAccess()).status).toBe("none");

    await user.click(within(done).getByRole("button", { name: "Ingresar de nuevo" }));
    expect(await screen.findByRole("heading", { name: "Ingresar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/ingresar");
  });
});
