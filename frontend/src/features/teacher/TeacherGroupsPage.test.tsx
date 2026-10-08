/**
 * T142: «Mis grupos» del docente (FR-027): ve el nombre de sus estudiantes, nunca el correo.
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import type { GroupStudent, GroupSummary } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import { page, renderAt } from "@/features/admin/testing";

const GROUP: GroupSummary = {
  id: "0192f3c4-0000-7000-8000-0000000000f1",
  name: "Derecho 2026-2",
  cohort_label: "2026-2",
  member_count: 2,
};

const STUDENTS: GroupStudent[] = [
  { user_id: "0192f3c4-0000-7000-8000-0000000000e1", display_name: "Ana Pérez" },
  { user_id: "0192f3c4-0000-7000-8000-0000000000e2", display_name: "Pedro Gómez" },
];

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

describe("mis grupos", () => {
  it("lista los grupos del docente y los nombres de sus estudiantes sin correos", async () => {
    server.use(
      http.get("/api/v1/teacher/groups", () => HttpResponse.json([GROUP])),
      http.get("/api/v1/teacher/groups/:id/students", () => HttpResponse.json(page(STUDENTS))),
    );
    renderAt("/grupos", "teacher");
    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Mis grupos" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /derecho 2026-2/i }));

    const list = await screen.findByRole("list", { name: "Estudiantes de Derecho 2026-2" });
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Ana Pérez", "Pedro Gómez"]);
    expect(document.body.textContent).not.toContain("@");
  });

  it("sin grupos lo explica", async () => {
    server.use(http.get("/api/v1/teacher/groups", () => HttpResponse.json([])));
    renderAt("/grupos", "teacher");

    expect(await screen.findByText(/todavía no tienes grupos asignados/i)).toBeInTheDocument();
  });
});
