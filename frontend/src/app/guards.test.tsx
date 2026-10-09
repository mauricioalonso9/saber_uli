/**
 * T066: guardias de navegación (FR-014, FR-019 a FR-022, FR-030, FR-039; research R-35).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Me, Permission } from "@/api/model";
import { App } from "@/app/App";
import { type SessionState, decideNavigation } from "@/app/guards";
import { createAppRouter } from "@/app/router";

function me(overrides: Partial<Me> = {}, permissions: Permission[] = []): Me {
  return {
    id: "0192f3c4-0000-7000-8000-000000000001",
    kind: "institutional",
    status: "active",
    display_name: "Ana",
    email: "ana@unilibre.edu.co",
    roles: ["student"],
    permissions,
    onboarding: { consent_required: false, profile_required: false },
    access: {
      valid: true,
      validated_at: "2026-10-06T12:00:00Z",
      offline_grace_until: "2026-10-13T12:00:00Z",
    },
    ...overrides,
  };
}

const anonymous: SessionState = { kind: "anonymous" };
const signedIn = (value: Me): SessionState => ({ kind: "authenticated", me: value });

describe("decideNavigation", () => {
  it("sin sesión lleva a /ingresar recordando a dónde iba", () => {
    expect(decideNavigation(anonymous, "/mi-cuenta")).toBe("/ingresar?return_to=%2Fmi-cuenta");
  });

  it.each(["/ingresar", "/acceso"])("sin sesión %s es accesible", (path) => {
    expect(decideNavigation(anonymous, path)).toBeNull();
  });

  it("con sesión, /ingresar lleva a /inicio", () => {
    expect(decideNavigation(signedIn(me()), "/ingresar")).toBe("/inicio");
  });

  it("sin autorización de datos lleva a /bienvenida/datos (FR-014)", () => {
    const pending = me({ onboarding: { consent_required: true, profile_required: true } });

    expect(decideNavigation(signedIn(pending), "/inicio")).toBe("/bienvenida/datos");
    expect(decideNavigation(signedIn(pending), "/bienvenida/perfil")).toBe("/bienvenida/datos");
    expect(decideNavigation(signedIn(pending), "/bienvenida/datos")).toBeNull();
  });

  it("sin autorización de datos deja solicitar la supresión (FR-014, escenario 2.3)", () => {
    const pending = me({ onboarding: { consent_required: true, profile_required: true } });

    expect(decideNavigation(signedIn(pending), "/mi-cuenta/datos")).toBeNull();
    expect(decideNavigation(signedIn(pending), "/mi-cuenta/autorizacion")).toBe(
      "/bienvenida/datos",
    );
  });

  it("con autorización pero sin perfil lleva a /bienvenida/perfil (FR-019, FR-020)", () => {
    const pending = me({ onboarding: { consent_required: false, profile_required: true } });

    expect(decideNavigation(signedIn(pending), "/inicio")).toBe("/bienvenida/perfil");
    expect(decideNavigation(signedIn(pending), "/bienvenida/perfil")).toBeNull();
  });

  it("retoma el paso pendiente y no vuelve a pasos ya completados (FR-022)", () => {
    expect(decideNavigation(signedIn(me()), "/bienvenida/datos")).toBe("/inicio");
    expect(decideNavigation(signedIn(me()), "/bienvenida/perfil")).toBe("/inicio");
  });

  it.each<[string, Permission]>([
    ["/invitaciones", "invitations:manage_own"],
    ["/grupos", "groups:read_own_students"],
    ["/admin/usuarios", "users:manage"],
    ["/admin/grupos", "groups:manage"],
    ["/admin/programas", "programs:manage"],
    ["/admin/supresiones", "deletions:read"],
    ["/admin/politica", "policy:publish"],
    ["/admin/parametros", "settings:manage"],
    ["/admin/auditoria", "audit:read"],
  ])("%s exige %s (FR-030)", (path, permission) => {
    expect(decideNavigation(signedIn(me()), path)).toBe("/inicio");
    expect(decideNavigation(signedIn(me({}, [permission])), path)).toBeNull();
  });

  it("un administrador con invitations:manage_all también entra a /invitaciones", () => {
    expect(
      decideNavigation(signedIn(me({}, ["invitations:manage_all"])), "/invitaciones"),
    ).toBeNull();
  });

  it("más de 7 días sin conexión bloquea todo salvo el aviso (FR-039)", () => {
    const expired: SessionState = { kind: "offline-expired" };

    expect(decideNavigation(expired, "/inicio")).toBe("/sin-conexion");
    expect(decideNavigation(expired, "/sin-conexion")).toBeNull();
  });
});

describe("guardias en el router", () => {
  async function landOn(path: string, session: SessionState) {
    const router = createAppRouter({
      initialPath: path,
      getSession: () => Promise.resolve(session),
    });
    render(<App router={router} />);
    await screen.findByRole("main");
    await new Promise((resolve) => setTimeout(resolve, 0));
    return router;
  }

  it("sin sesión termina en /ingresar", async () => {
    const router = await landOn("/inicio", anonymous);

    expect(await screen.findByRole("heading", { name: "Ingresar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/ingresar");
  });

  it("con la autorización pendiente termina en /bienvenida/datos", async () => {
    const pending = me({ onboarding: { consent_required: true, profile_required: false } });
    const router = await landOn("/inicio", signedIn(pending));

    expect(
      await screen.findByRole("heading", { name: "Tratamiento de tus datos" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/bienvenida/datos");
  });

  it("sin conexión por más de 7 días muestra el aviso", async () => {
    await landOn("/inicio", { kind: "offline-expired" });

    expect(await screen.findByText(/conéctate a internet/i)).toBeInTheDocument();
  });
});
