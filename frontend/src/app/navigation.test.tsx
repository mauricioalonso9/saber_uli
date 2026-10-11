/**
 * T033: entradas del banco de ítems en la navegación y guardias de sus rutas (002; research R-08,
 * R-17). Sin el permiso, la ruta vuelve a /inicio como el resto de rutas de gestión (FR-030 de
 * 001); la API responde 403 de todas formas.
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Me, Permission } from "@/api/model";
import { App } from "@/app/App";
import { decideNavigation } from "@/app/guards";
import { createAppRouter } from "@/app/router";

function me(permissions: Permission[] = []): Me {
  return {
    id: "0192f3c4-0000-7000-8000-000000000001",
    kind: "institutional",
    status: "active",
    display_name: "Ana",
    email: "ana@unilibre.edu.co",
    roles: ["teacher"],
    permissions,
    onboarding: {
      consent_required: false,
      profile_required: false,
      password_change_required: false,
    },
    access: {
      valid: true,
      validated_at: "2026-10-06T12:00:00Z",
      offline_grace_until: "2026-10-13T12:00:00Z",
    },
  };
}

async function navLinks(permissions: Permission[]) {
  const router = createAppRouter({
    initialPath: "/inicio",
    getSession: () => Promise.resolve({ kind: "authenticated", me: me(permissions) }),
  });
  render(<App router={router} />);
  await screen.findByRole("heading", { name: "Inicio" });
  const nav = screen.getByRole("navigation", { name: "Principal" });
  return within(nav)
    .getAllByRole("link")
    .map((link) => link.textContent);
}

describe("navegación del banco de ítems", () => {
  it("un estudiante no ve el banco", async () => {
    const links = await navLinks([]);

    expect(links).not.toContain("Banco de ítems");
    expect(links).not.toContain("Revisión de ítems");
    expect(links).not.toContain("Taxonomía");
  });

  it("un docente ve el banco, pero no la revisión ni la taxonomía", async () => {
    const links = await navLinks(["content:author"]);

    expect(links).toContain("Banco de ítems");
    expect(links).not.toContain("Revisión de ítems");
    expect(links).not.toContain("Taxonomía");
  });

  it("un administrador ve también la revisión y la taxonomía", async () => {
    const links = await navLinks(["content:author", "content:review", "content:taxonomy_manage"]);

    expect(links).toEqual(
      expect.arrayContaining(["Banco de ítems", "Revisión de ítems", "Taxonomía"]),
    );
  });

  it.each<[string, Permission]>([
    ["/banco", "content:author"],
    ["/banco/items/LC-0001", "content:author"],
    ["/banco/importar", "content:author"],
    ["/banco/cobertura", "content:author"],
    ["/banco/revision", "content:review"],
    ["/admin/taxonomia", "content:taxonomy_manage"],
  ])("%s exige %s", (path, permission) => {
    const session = (permissions: Permission[]) =>
      ({ kind: "authenticated", me: me(permissions) }) as const;

    expect(decideNavigation(session([]), path)).toBe("/inicio");
    expect(decideNavigation(session([permission]), path)).toBeNull();
  });

  it("la revisión no basta con content:author", () => {
    expect(
      decideNavigation({ kind: "authenticated", me: me(["content:author"]) }, "/banco/revision"),
    ).toBe("/inicio");
  });
});
