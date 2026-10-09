/**
 * T043: acciones de revisión sobre un ítem (US2; FR-012 a FR-014; research R-09).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Item } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ReviewActions } from "@/features/content/ReviewActions";
import { item } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

interface Call {
  action: string;
  ifMatch: string | null;
  body: unknown;
}

let calls: Call[];

function serve(response?: { status: number; type: string }) {
  calls = [];
  server.use(
    http.post("/api/v1/content/items/:code/:action", async ({ request, params }) => {
      calls.push({
        action: String(params.action),
        ifMatch: request.headers.get("If-Match"),
        body: await request.json(),
      });
      if (response) {
        return HttpResponse.json(
          { type: `urn:saber-uli:problem:${response.type}`, title: "x", status: response.status },
          { status: response.status, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return HttpResponse.json(item({ revision: 1 }), { headers: { ETag: '"1"' } });
    }),
  );
}

function renderActions(value: Item) {
  const onChanged = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ReviewActions item={value} onChanged={onChanged} />
    </QueryClientProvider>,
  );
  return onChanged;
}

describe("acciones de revisión", () => {
  it("aprobar exige marcar las dos confirmaciones y envía If-Match", async () => {
    serve();
    const onChanged = renderActions(item({ revision: 3 }));
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Aprobar" }));
    const confirm = screen.getByRole("button", { name: "Publicar" });
    expect(confirm).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /alineado con la guía del ICFES/ }));
    expect(confirm).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /no reproduce preguntas del ICFES/ }));
    await user.click(confirm);

    expect(await screen.findByRole("status")).toHaveTextContent("El ítem quedó publicado.");
    expect(calls).toEqual([
      {
        action: "approval",
        ifMatch: '"3"',
        body: { confirms_alignment: true, confirms_originality: true },
      },
    ]);
    expect(onChanged).toHaveBeenCalled();
  });

  it("devolver exige un comentario", async () => {
    serve();
    renderActions(item());
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Devolver" }));
    const send = screen.getByRole("button", { name: "Devolver al autor" });
    expect(send).toBeDisabled();
    await user.type(screen.getByLabelText("Comentario para el autor"), "Revisa la opción C.");
    await user.click(send);

    expect(await screen.findByRole("status")).toHaveTextContent("El ítem volvió a Borrador.");
    expect(calls[0]).toMatchObject({ action: "return", body: { comment: "Revisa la opción C." } });
  });

  it("rechazar exige un motivo", async () => {
    serve();
    renderActions(item());
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Rechazar" }));
    await user.type(screen.getByLabelText("Motivo"), "Reproduce una pregunta del ICFES.");
    await user.click(screen.getByRole("button", { name: "Rechazar el ítem" }));

    expect(await screen.findByRole("status")).toHaveTextContent("El ítem quedó rechazado.");
    expect(calls[0]).toMatchObject({ action: "rejection" });
  });

  it("retirar un publicado exige un motivo", async () => {
    serve();
    renderActions(
      item({
        open: null,
        can: {
          edit: true,
          submit: false,
          approve: false,
          return: false,
          reject: false,
          retire: true,
          approve_blocked_reason: null,
        },
      }),
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Retirar" }));
    await user.type(screen.getByLabelText("Motivo"), "Ambiguo.");
    await user.click(screen.getByRole("button", { name: "Retirar el ítem" }));

    expect(await screen.findByRole("status")).toHaveTextContent("El ítem quedó retirado.");
    expect(calls[0]).toMatchObject({ action: "retirement", body: { reason: "Ambiguo." } });
  });

  it("explica la autoaprobación", async () => {
    serve();
    renderActions(
      item({
        can: {
          edit: true,
          submit: false,
          approve: false,
          return: true,
          reject: true,
          retire: false,
          approve_blocked_reason: "self_approval",
        },
      }),
    );

    expect(screen.queryByRole("button", { name: "Aprobar" })).toBeNull();
    expect(
      screen.getByText("Modificaste esta versión: la debe aprobar otro administrador."),
    ).toBeInTheDocument();
  });

  it("un 403 de autoaprobación se muestra en español", async () => {
    serve({ status: 403, type: "self-approval-forbidden" });
    renderActions(item());
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Aprobar" }));
    await user.click(screen.getByRole("checkbox", { name: /alineado con la guía del ICFES/ }));
    await user.click(screen.getByRole("checkbox", { name: /no reproduce preguntas del ICFES/ }));
    await user.click(screen.getByRole("button", { name: "Publicar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Lo debe aprobar otro administrador",
    );
  });

  it("un docente solo puede comentar", async () => {
    serve();
    renderActions(
      item({
        can: {
          edit: true,
          submit: false,
          approve: false,
          return: false,
          reject: false,
          retire: false,
          approve_blocked_reason: null,
        },
      }),
    );

    expect(screen.queryByRole("button", { name: "Aprobar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Devolver" })).toBeNull();
    expect(screen.getByRole("button", { name: "Comentar" })).toBeInTheDocument();
  });

  it("comentar deja el comentario en la historia", async () => {
    serve();
    server.use(
      http.post("/api/v1/content/items/:code/comments", async ({ request }) => {
        calls.push({ action: "comments", ifMatch: null, body: await request.json() });
        return HttpResponse.json(
          {
            id: "0192f3c4-0000-7000-8000-0000000000c1",
            type: "commented",
            version: 1,
            actor: { id: "0192f3c4-0000-7000-8000-0000000000a1", display_name: "Ana" },
            occurred_at: "2026-10-09T12:00:00Z",
            comment: "¿La B es ambigua?",
            reason: null,
            details: {},
          },
          { status: 201 },
        );
      }),
    );
    const onChanged = renderActions(item());
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Comentar" }));
    await user.type(screen.getByLabelText("Comentario"), "¿La B es ambigua?");
    await user.click(screen.getByRole("button", { name: "Publicar comentario" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Comentario publicado.");
    expect(calls[0]).toMatchObject({ action: "comments", body: { comment: "¿La B es ambigua?" } });
    expect(onChanged).toHaveBeenCalled();
  });
});
