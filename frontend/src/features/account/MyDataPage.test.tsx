/**
 * T167: consultar y descargar mis datos (FR-031; escenarios 8.1 y 8.2).
 */
import "fake-indexeddb/auto";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Me, PersonalDataExport } from "@/api/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

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

const DIRECTORY_NOTE =
  "Tu nombre y tu correo vienen del directorio institucional de Unilibre. Para corregirlos, " +
  "escribe a la mesa de ayuda de TI; se actualizan aquí en tu siguiente ingreso.";

const EXPORT: PersonalDataExport = {
  generated_at: "2026-10-08T15:00:00Z",
  identity: {
    id: ME.id,
    kind: "institutional",
    display_name: "Ana Pérez",
    email: "ana.perez@unilibre.edu.co",
    created_at: "2026-10-01T13:00:00Z",
    last_login_at: "2026-10-08T14:00:00Z",
    source_note: DIRECTORY_NOTE,
  },
  profile: {
    program: {
      id: "0192f3c4-0000-7000-8000-0000000000b1",
      code: "DER-BOG",
      name: "Derecho",
      campus: "Bogotá",
      active: true,
    },
    semester: 8,
    expected_exam_date: "2027-05-30",
    daily_goal: "regular",
    complete: true,
  },
  roles: ["student", "teacher"],
  groups: ["Saber Pro 2027-1"],
  consents: [
    {
      id: "0192f3c4-0000-7000-8000-0000000000c1",
      policy_version_id: "0192f3c4-0000-7000-8000-0000000000a1",
      policy_version: "1.0",
      decision: "accepted",
      channel: "web_pwa",
      decided_at: "2026-10-01T13:05:00Z",
    },
  ],
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
  vi.unstubAllGlobals();
});
afterAll(() => server.close());

function renderMyData(data: PersonalDataExport = EXPORT, me: Me = ME) {
  server.use(http.get("/api/v1/me/data-export", () => HttpResponse.json(data)));
  const router = createAppRouter({
    initialPath: "/mi-cuenta/datos",
    getSession: createSessionLoader(() => Promise.resolve({ kind: "authenticated", me })),
  });
  render(<App router={router} />);
  return router;
}

describe("mis datos", () => {
  it("muestra identidad, perfil, roles, grupos y autorizaciones (escenario 8.1)", async () => {
    renderMyData();

    expect(await screen.findByRole("heading", { name: "Mis datos", level: 1 })).toBeVisible();
    const identity = await screen.findByRole("region", { name: "Identidad" });
    expect(identity).toHaveTextContent("Ana Pérez");
    expect(identity).toHaveTextContent("ana.perez@unilibre.edu.co");
    expect(identity).toHaveTextContent("Cuenta institucional");
    const profile = screen.getByRole("region", { name: "Perfil" });
    expect(profile).toHaveTextContent("Derecho (Bogotá)");
    expect(profile).toHaveTextContent("8");
    expect(screen.getByRole("region", { name: "Roles" })).toHaveTextContent(/estudiante.*docente/i);
    expect(screen.getByRole("region", { name: "Grupos" })).toHaveTextContent("Saber Pro 2027-1");
    const consents = screen.getByRole("region", { name: "Historial de autorizaciones" });
    expect(within(consents).getAllByRole("listitem")[0]).toHaveTextContent(/aceptaste/i);
  });

  it("explica cómo corregir los datos del directorio (escenario 8.2)", async () => {
    renderMyData();

    const note = await screen.findByRole("note", { name: /algún dato está mal/i });
    expect(note).toHaveTextContent("directorio institucional");
    expect(within(note).getByRole("link", { name: "Editar mi perfil" })).toHaveAttribute(
      "href",
      "/mi-cuenta",
    );
  });

  it("al invitado no le habla del directorio", async () => {
    const guestNote = "Tu nombre lo indicas en tu perfil; tu correo es el de tu invitación.";
    renderMyData(
      {
        ...EXPORT,
        identity: { ...EXPORT.identity, kind: "guest", source_note: guestNote },
        roles: ["guest"],
        invitation: {
          accepted_at: "2026-10-01T13:00:00Z",
          access_expires_at: "2026-12-30T05:00:00Z",
        },
      },
      { ...ME, kind: "guest", roles: ["guest"] },
    );

    const note = await screen.findByRole("note", { name: /algún dato está mal/i });
    expect(note).toHaveTextContent(guestNote);
    expect(note).not.toHaveTextContent("directorio");
    expect(screen.getByRole("region", { name: "Invitación" })).toHaveTextContent(
      /30 de diciembre de 2026/,
    );
  });

  it("descarga una copia en JSON", async () => {
    const createObjectURL = vi.fn<(blob: Blob) => string>(() => "blob:mis-datos");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() }));
    const clicked: HTMLAnchorElement[] = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this);
    });
    renderMyData();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Descargar una copia" }));

    expect(click).toHaveBeenCalledOnce();
    expect(clicked[0]?.download).toMatch(/^saber-uli-mis-datos-\d{4}-\d{2}-\d{2}\.json$/);
    const blob = createObjectURL.mock.calls[0]?.[0];
    expect(blob?.type).toBe("application/json");
    expect(JSON.parse(await blob!.text())).toEqual(EXPORT);
    click.mockRestore();
  });

  it("incluye la solicitud de supresión de la cuenta", async () => {
    renderMyData();

    expect(await screen.findByRole("region", { name: "Eliminar mi cuenta" })).toBeVisible();
  });
});
