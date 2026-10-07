/**
 * T086: autorización de datos en el primer ingreso (FR-014 a FR-016; escenarios 2.1 a 2.3).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Consent, Me, PolicyVersion } from "@/api/model";
import { App } from "@/app/App";
import type { SessionState } from "@/app/guards";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const POLICY: PolicyVersion = {
  id: "0192f3c4-0000-7000-8000-0000000000a1",
  version: "1.0",
  title: "Política de tratamiento de datos personales de Saber Uli",
  effective_from: "2026-10-01T05:00:00Z",
  body_markdown: [
    "# Política de tratamiento de datos personales de Saber Uli",
    "",
    "## 2. Finalidades",
    "",
    "Usamos sus datos para identificarle y medir su progreso.",
    "",
    "## 3. Datos que recogemos",
    "",
    "- Nombre y correo institucional.",
    "",
    "## 5. Sus derechos",
    "",
    "Conocer, actualizar, rectificar y suprimir sus datos.",
    "",
    "## 6. Cómo ejercer sus derechos",
    "",
    "Escriba al correo de protección de datos.",
    "",
    '<img src="x" onerror="alert(1)"> <script>alert(2)</script>',
  ].join("\n"),
};

function me(onboarding: Me["onboarding"]): Me {
  return {
    id: "0192f3c4-0000-7000-8000-000000000001",
    kind: "institutional",
    status: "active",
    display_name: "Ana",
    email: "ana@unilibre.edu.co",
    roles: ["student"],
    permissions: [],
    onboarding,
    access: {
      valid: true,
      validated_at: "2026-10-07T12:00:00Z",
      offline_grace_until: "2026-10-14T12:00:00Z",
    },
  };
}

function consent(decision: Consent["decision"]): Consent {
  return {
    id: "0192f3c4-0000-7000-8000-0000000000c1",
    policy_version_id: POLICY.id,
    policy_version: POLICY.version,
    decision,
    channel: "web_pwa",
    decided_at: "2026-10-07T15:30:00Z",
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

let session: SessionState;
let decisions: unknown[];

function renderConsent() {
  session = {
    kind: "authenticated",
    me: me({ consent_required: true, profile_required: true }),
  };
  decisions = [];
  server.use(
    http.get("/api/v1/privacy-policy/current", () => HttpResponse.json(POLICY)),
    http.post("/api/v1/me/consents", async ({ request }) => {
      const body = (await request.json()) as { decision: Consent["decision"] };
      decisions.push(body);
      if (body.decision === "accepted") {
        session = {
          kind: "authenticated",
          me: me({ consent_required: false, profile_required: true }),
        };
      }
      return HttpResponse.json(consent(body.decision), { status: 201 });
    }),
  );
  const router = createAppRouter({
    initialPath: "/bienvenida/datos",
    getSession: createSessionLoader(() => Promise.resolve(session)),
  });
  render(<App router={router} />);
  return router;
}

async function choose(name: "Acepto" | "No acepto") {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("radio", { name }));
  await user.click(screen.getByRole("button", { name: "Confirmar mi decisión" }));
}

describe("página de autorización de datos", () => {
  it("muestra la finalidad, los datos, los derechos y los canales de la política vigente", async () => {
    renderConsent();

    const policy = await screen.findByRole("article", { name: POLICY.title });
    for (const heading of [
      "2. Finalidades",
      "3. Datos que recogemos",
      "5. Sus derechos",
      "6. Cómo ejercer sus derechos",
    ]) {
      expect(within(policy).getByRole("heading", { name: heading })).toBeInTheDocument();
    }
    expect(screen.getByText(/versión 1\.0/i)).toBeInTheDocument();
  });

  it("no interpreta el HTML incrustado en el texto de la política", async () => {
    renderConsent();

    const policy = await screen.findByRole("article", { name: POLICY.title });
    expect(policy.querySelector("img, script")).toBeNull();
  });

  it("ofrece Acepto y No acepto sin ninguna opción preseleccionada (FR-015)", async () => {
    renderConsent();

    const group = await screen.findByRole("radiogroup", { name: /tu decisión/i });
    expect(within(group).getAllByRole("radio")).toHaveLength(2);
    expect(within(group).getByRole("radio", { name: "Acepto" })).not.toBeChecked();
    expect(within(group).getByRole("radio", { name: "No acepto" })).not.toBeChecked();
  });

  it("confirmar sin elegir pide escoger una opción y no envía nada", async () => {
    renderConsent();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Confirmar mi decisión" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/elige una opción/i);
    expect(decisions).toEqual([]);
  });

  it("Acepto registra la decisión sobre la versión vigente y continúa al perfil", async () => {
    const router = renderConsent();

    await choose("Acepto");

    expect(await screen.findByRole("heading", { name: "Completa tu perfil" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/bienvenida/perfil");
    expect(decisions).toEqual([{ policy_version_id: POLICY.id, decision: "accepted" }]);
  });

  it("No acepto explica el bloqueo y ofrece aceptar luego o solicitar la supresión", async () => {
    const router = renderConsent();
    const user = userEvent.setup();

    await choose("No acepto");

    const explanation = await screen.findByRole("region", { name: /no aceptaste/i });
    expect(explanation).toHaveTextContent(/no puedes usar ninguna función/i);
    expect(
      within(explanation).getByRole("link", { name: /solicitar la eliminación de mi cuenta/i }),
    ).toHaveAttribute("href", "/mi-cuenta/datos");
    expect(decisions).toEqual([{ policy_version_id: POLICY.id, decision: "rejected" }]);
    expect(router.state.location.pathname).toBe("/bienvenida/datos");

    await user.click(
      within(explanation).getByRole("button", { name: /revisar la política y aceptar/i }),
    );
    expect(await screen.findByRole("radio", { name: "Acepto" })).not.toBeChecked();
  });

  it("si la política cambió mientras la leía, avisa y muestra la versión nueva", async () => {
    renderConsent();
    const updated: PolicyVersion = { ...POLICY, id: `${POLICY.id.slice(0, -1)}2`, version: "1.1" };
    server.use(
      http.post("/api/v1/me/consents", () =>
        HttpResponse.json(
          {
            type: "urn:saber-uli:problem:policy-version-not-current",
            title: "Conflicto",
            status: 409,
          },
          { status: 409, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
      http.get("/api/v1/privacy-policy/current", () => HttpResponse.json(updated)),
    );

    await choose("Acepto");

    expect(await screen.findByRole("alert")).toHaveTextContent(/la política cambió/i);
    expect(await screen.findByText(/versión 1\.1/i)).toBeInTheDocument();
  });
});
