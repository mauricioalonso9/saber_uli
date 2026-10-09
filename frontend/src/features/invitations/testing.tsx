/**
 * Ayudantes de las pruebas de `/invitaciones` (T127): sesión de docente o administrador y datos
 * de ejemplo con la forma del contrato.
 */
import { render } from "@testing-library/react";

import type { Invitation, Me } from "@/api/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

export const TEACHER_ID = "0192f3c4-0000-7000-8000-0000000000a1";

export function staff(kind: "teacher" | "admin"): Me {
  return {
    id: TEACHER_ID,
    kind: "institutional",
    status: "active",
    display_name: kind === "admin" ? "Administración" : "Docente Pérez",
    email: "docente@unilibre.edu.co",
    roles: kind === "admin" ? ["admin", "student"] : ["student", "teacher"],
    permissions:
      kind === "admin"
        ? ["invitations:manage_all", "invitations:manage_own"]
        : ["invitations:manage_own", "groups:read_own_students"],
    onboarding: { consent_required: false, profile_required: false },
    access: {
      valid: true,
      validated_at: "2026-10-07T12:00:00Z",
      offline_grace_until: "2026-10-14T12:00:00Z",
      privileged_session: true,
    },
  };
}

export function invitation(overrides: Partial<Invitation> = {}): Invitation {
  return {
    id: "0192f3c4-0000-7000-8000-0000000000c1",
    email: "laura@correo.co",
    invitee_name: "Laura Gómez",
    status: "sent",
    access_expires_at: "2027-01-05T04:59:59Z",
    invited_by: { id: TEACHER_ID, display_name: "Docente Pérez" },
    created_at: "2026-10-07T15:00:00Z",
    delivery_status: "sent",
    ...overrides,
  };
}

export function renderInvitations(kind: "teacher" | "admin") {
  useSessionStore.getState().setSession("token", 600);
  const router = createAppRouter({
    initialPath: "/invitaciones",
    getSession: createSessionLoader(() =>
      Promise.resolve({ kind: "authenticated" as const, me: staff(kind) }),
    ),
  });
  render(<App router={router} />);
  return router;
}
