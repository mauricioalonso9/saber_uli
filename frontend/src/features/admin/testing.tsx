/**
 * Ayudantes de las pruebas de administración y del docente (T142): sesión con los permisos
 * pedidos y la app montada en una ruta.
 */
import { render } from "@testing-library/react";

import type { Me, Permission, Role } from "@/api/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

export const ME_ID = "0192f3c4-0000-7000-8000-0000000000a1";

const ADMIN_PERMISSIONS: Permission[] = [
  "users:manage",
  "groups:manage",
  "programs:manage",
  "settings:manage",
  "audit:read",
  "policy:publish",
  "invitations:manage_all",
  "invitations:manage_own",
  "groups:read_own_students",
  "deletions:read",
  "programs:read_aggregated",
];

export function sessionFor(kind: "admin" | "teacher"): Me {
  const roles: Role[] = kind === "admin" ? ["admin", "student"] : ["student", "teacher"];
  return {
    id: ME_ID,
    kind: "institutional",
    status: "active",
    display_name: kind === "admin" ? "Administración" : "Docente Pérez",
    email: "persona@unilibre.edu.co",
    roles,
    permissions:
      kind === "admin" ? ADMIN_PERMISSIONS : ["invitations:manage_own", "groups:read_own_students"],
    onboarding: { consent_required: false, profile_required: false },
    access: {
      valid: true,
      validated_at: "2026-10-07T12:00:00Z",
      offline_grace_until: "2026-10-14T12:00:00Z",
      privileged_session: true,
    },
  };
}

export function renderAt(path: string, kind: "admin" | "teacher" = "admin") {
  useSessionStore.getState().setSession("token", 600);
  const router = createAppRouter({
    initialPath: path,
    getSession: createSessionLoader(() =>
      Promise.resolve({ kind: "authenticated" as const, me: sessionFor(kind) }),
    ),
  });
  render(<App router={router} />);
  return router;
}

export function page<T>(items: T[]) {
  return { page: 1, page_size: 100, total: items.length, items };
}

export function problemResponse(status: number, slug: string, detail?: string) {
  return {
    body: { type: `urn:saber-uli:problem:${slug}`, title: "Error", status, detail },
    init: { status, headers: { "Content-Type": "application/problem+json" } },
  };
}
