/**
 * T178b: ver y cerrar las sesiones abiertas desde Mi cuenta (FR-037a; escenario 1.5).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { MySession } from "@/api/model";
import { SessionsSection } from "@/features/account/SessionsSection";
import { useSessionStore } from "@/features/auth/session-store";

const CURRENT: MySession = {
  id: "0192f3c4-0000-7000-8000-0000000000a1",
  auth_method: "entra_id",
  started_at: "2026-10-08T12:00:00Z",
  last_activity_at: "2026-10-08T14:00:00Z",
  current: true,
};
const PHONE: MySession = {
  ...CURRENT,
  id: "0192f3c4-0000-7000-8000-0000000000a2",
  started_at: "2026-10-01T09:00:00Z",
  last_activity_at: "2026-10-07T20:00:00Z",
  current: false,
};
const TABLET: MySession = { ...PHONE, id: "0192f3c4-0000-7000-8000-0000000000a3" };

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let sessions: MySession[];
let revoked: string[];

function renderSection() {
  revoked = [];
  server.use(
    http.get("/api/v1/me/sessions", () => HttpResponse.json({ items: sessions })),
    http.post("/api/v1/me/sessions/:id/revocation", ({ params }) => {
      revoked.push(String(params.id));
      sessions = sessions.filter((session) => session.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
    http.post("/api/v1/me/sessions/revocation", () => {
      revoked.push("others");
      sessions = sessions.filter((session) => session.current);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <SessionsSection />
    </QueryClientProvider>,
  );
}

describe("sesiones abiertas", () => {
  it("muestra cada sesión con su forma de ingreso y marca la de este dispositivo", async () => {
    sessions = [CURRENT, PHONE];
    renderSection();

    const list = await screen.findByRole("list");
    const items = await within(list).findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent(/Cuenta Unilibre \(Microsoft 365\) \(este dispositivo\)/);
    expect(within(items[0]).queryByRole("button")).toBeNull();
    expect(items[1]).toHaveTextContent(/Última actividad/);
  });

  it("cierra otra sesión y lo confirma", async () => {
    sessions = [CURRENT, PHONE];
    renderSection();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /Cerrar la sesión de Cuenta/ }));

    expect(await screen.findByText(/La sesión se cerró/)).toHaveAttribute("role", "status");
    expect(revoked).toEqual([PHONE.id]);
    expect(await within(screen.getByRole("list")).findAllByRole("listitem")).toHaveLength(1);
  });

  it("cierra todas las demás de una vez", async () => {
    sessions = [CURRENT, PHONE, TABLET];
    renderSection();
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: "Cerrar todas las demás sesiones" }),
    );

    expect(await screen.findByText(/Se cerraron las demás sesiones/)).toBeInTheDocument();
    expect(revoked).toEqual(["others"]);
    expect(screen.queryByRole("button", { name: "Cerrar todas las demás sesiones" })).toBeNull();
  });

  it("sin otras sesiones no ofrece cerrarlas", async () => {
    sessions = [CURRENT];
    renderSection();

    expect(await screen.findByText(/este dispositivo/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
