/**
 * T127: invitar a una persona (FR-006, FR-006a, FR-008; escenarios 5.1, 5.3 y 5.8).
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import { useSessionStore } from "@/features/auth/session-store";
import { invitation, renderInvitations } from "@/features/invitations/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let created: unknown[];

function mockApi() {
  created = [];
  server.use(
    http.get("/api/v1/invitations", () =>
      HttpResponse.json({ page: 1, page_size: 25, total: 0, items: [] }),
    ),
    http.post("/api/v1/invitations", async ({ request }) => {
      created.push(await request.json());
      return HttpResponse.json(invitation(), { status: 201 });
    }),
  );
}

async function form() {
  return screen.findByRole("form", { name: /invitar a una persona/i });
}

describe("invitar a una persona", () => {
  it("envía correo, nombre y vencimiento al final del día elegido en Colombia", async () => {
    mockApi();
    renderInvitations("teacher");
    const user = userEvent.setup();
    const invite = await form();

    await user.type(within(invite).getByRole("textbox", { name: "Correo" }), "laura@correo.co");
    await user.type(within(invite).getByRole("textbox", { name: /nombre/i }), "Laura Gómez");
    await user.type(within(invite).getByLabelText(/acceso hasta/i), "2027-01-04");
    await user.click(within(invite).getByRole("button", { name: "Enviar invitación" }));

    expect(await screen.findByText(/enviamos la invitación/i)).toBeInTheDocument();
    expect(created).toEqual([
      {
        email: "laura@correo.co",
        invitee_name: "Laura Gómez",
        access_expires_at: "2027-01-04T23:59:59-05:00",
      },
    ]);
  });

  it("sin fecha deja que se use el plazo por defecto", async () => {
    mockApi();
    renderInvitations("teacher");
    const user = userEvent.setup();
    const invite = await form();

    await user.type(within(invite).getByRole("textbox", { name: "Correo" }), "laura@correo.co");
    await user.click(within(invite).getByRole("button", { name: "Enviar invitación" }));

    await screen.findByText(/enviamos la invitación/i);
    expect(created).toEqual([{ email: "laura@correo.co" }]);
  });

  it("valida el correo y que la fecha sea futura sin enviar nada", async () => {
    mockApi();
    renderInvitations("teacher");
    const user = userEvent.setup();
    const invite = await form();

    await user.type(within(invite).getByRole("textbox", { name: "Correo" }), "no-es-correo");
    await user.type(within(invite).getByLabelText(/acceso hasta/i), "2020-01-01");
    await user.click(within(invite).getByRole("button", { name: "Enviar invitación" }));

    const email = within(invite).getByRole("textbox", { name: "Correo" });
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveAccessibleDescription(/correo válido/i);
    expect(within(invite).getByLabelText(/acceso hasta/i)).toHaveAccessibleDescription(
      /fecha futura/i,
    );
    expect(created).toEqual([]);
  });

  it.each([
    ["access-expiry-out-of-range", "El acceso puede durar como máximo 180 días.", /180 días/],
    [
      "institutional-email-not-invitable",
      "Las personas con correo institucional ingresan con su cuenta Unilibre.",
      /cuenta unilibre/i,
    ],
  ])("muestra el rechazo del servidor %s", async (slug, detail, message) => {
    mockApi();
    server.use(
      http.post("/api/v1/invitations", () =>
        HttpResponse.json(
          { type: `urn:saber-uli:problem:${slug}`, title: "Error", status: 422, detail },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    renderInvitations("teacher");
    const user = userEvent.setup();
    const invite = await form();

    await user.type(within(invite).getByRole("textbox", { name: "Correo" }), "laura@correo.co");
    await user.click(within(invite).getByRole("button", { name: "Enviar invitación" }));

    expect(await within(invite).findByRole("alert")).toHaveTextContent(message);
  });
});
