/**
 * T112: un invitado pide un enlace de ingreso (FR-013): la página muestra el mismo mensaje exista
 * o no el correo.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

let requested: unknown[];

function renderRequest() {
  requested = [];
  server.use(
    http.post("/api/auth/guest/link-requests", async ({ request }) => {
      requested.push(await request.json());
      return HttpResponse.json({ message: "Recibido" }, { status: 202 });
    }),
  );
  const router = createAppRouter({
    initialPath: "/ingresar/invitado",
    getSession: () => Promise.resolve({ kind: "anonymous" }),
  });
  render(<App router={router} />);
  return router;
}

async function ask(email: string) {
  const user = userEvent.setup();
  const field = await screen.findByRole("textbox", { name: "Tu correo" });
  await user.clear(field);
  await user.type(field, email);
  await user.click(screen.getByRole("button", { name: "Enviarme un enlace" }));
}

describe("pedir un enlace de ingreso", () => {
  it("muestra el mismo mensaje exista o no el correo", async () => {
    renderRequest();

    await ask("laura@correo.co");
    const first = (await screen.findByText(/si el correo corresponde/i)).textContent;
    await ask("nadie@correo.co");
    const second = (await screen.findByText(/si el correo corresponde/i)).textContent;

    expect(first).toBe(second);
    expect(requested).toEqual([{ email: "laura@correo.co" }, { email: "nadie@correo.co" }]);
  });

  it("valida el correo antes de enviar", async () => {
    renderRequest();

    await ask("no-es-correo");

    const field = screen.getByRole("textbox", { name: "Tu correo" });
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription(/correo válido/i);
    expect(requested).toEqual([]);
  });

  it("avisa cuando hay demasiadas solicitudes", async () => {
    renderRequest();
    server.use(
      http.post("/api/auth/guest/link-requests", () =>
        HttpResponse.json(
          { type: "urn:saber-uli:problem:rate-limited", title: "Error", status: 429 },
          {
            status: 429,
            headers: { "Content-Type": "application/problem+json", "Retry-After": "60" },
          },
        ),
      ),
    );

    await ask("laura@correo.co");

    expect(await screen.findByRole("alert")).toHaveTextContent(/demasiadas solicitudes/i);
  });

  it("permite volver al ingreso institucional", async () => {
    renderRequest();

    expect(await screen.findByRole("link", { name: /cuenta unilibre/i })).toHaveAttribute(
      "href",
      "/ingresar",
    );
  });
});
