/**
 * T055: editor de contextos (US3; FR-005, FR-007, FR-009, FR-020, FR-026).
 *
 * Antes de guardar un cambio avisa cuántos ítems usan el contexto y cuántos están publicados;
 * aplica las reglas del banco (texto alternativo, 500 palabras en Lectura crítica, opciones
 * compartidas de la parte con retroalimentación). El contador "501/500" de T054 vive aquí,
 * junto al texto que cuenta.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Context } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ContextEditor } from "@/features/content/ContextEditorPage";
import { MODULES } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => {
  useSessionStore.getState().setSession("token", 600);
  server.use(http.get("/api/v1/content/modules", () => HttpResponse.json({ items: MODULES })));
});
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

function context(overrides: Partial<Context> = {}): Context {
  return {
    code: "LC-CTX-301",
    module: "LC",
    kind: "text",
    title: "Desconectar para aprender",
    body_md: "Un texto breve de opinión.",
    text_type_node_id: "lc-tt",
    version: 1,
    word_count: 5,
    item_count: 3,
    published_item_count: 1,
    origin: "teacher",
    updated_at: "2026-10-09T12:00:00Z",
    revision: 4,
    items: [
      { code: "LC-0301", state: "published" },
      { code: "LC-0302", state: "draft" },
      { code: "LC-0303", state: "in_review" },
    ],
    ...overrides,
  };
}

function renderEditor(value?: Context) {
  const onSaved = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ContextEditor context={value} onSaved={onSaved} />
    </QueryClientProvider>,
  );
  return onSaved;
}

describe("editor de contextos", () => {
  it("avisa a cuántos ítems afecta el cambio antes de confirmarlo", async () => {
    let request: { ifMatch: string | null; body: unknown } | null = null;
    server.use(
      http.put("/api/v1/content/contexts/:code", async ({ request: sent }) => {
        request = { ifMatch: sent.headers.get("If-Match"), body: await sent.json() };
        return HttpResponse.json(
          {
            context: context({ revision: 5, version: 2 }),
            new_review_versions: ["LC-0301"],
            rebased_open_versions: ["LC-0302", "LC-0303"],
          },
          { headers: { ETag: '"5"' } },
        );
      }),
    );
    const onSaved = renderEditor(context());
    const user = userEvent.setup();

    const body = await screen.findByLabelText("Texto");
    await user.clear(body);
    await user.type(body, "Texto corregido por el docente.");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    const confirm = screen.getByRole("alertdialog", { name: "¿Guardar el cambio del contexto?" });
    expect(confirm).toHaveTextContent(
      "Este contexto lo usan 3 ítems; 1 está publicado y recibirá una versión nueva En revisión.",
    );
    expect(request).toBeNull();
    await user.click(within(confirm).getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Contexto guardado (versión 2). Pasaron a revisión: LC-0301.",
    );
    expect(request).toEqual({
      ifMatch: '"4"',
      body: expect.objectContaining({ body_md: "Texto corregido por el docente." }),
    });
    expect(onSaved).toHaveBeenCalled();
  });

  it("cuenta las palabras y marca el exceso en Lectura crítica", async () => {
    renderEditor(context());
    const user = userEvent.setup();
    const body = await screen.findByLabelText("Texto");

    await user.clear(body);
    await user.click(body);
    await user.paste(Array(501).fill("palabra").join(" "));

    expect(screen.getByText("501/500 palabras")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(body).toHaveAccessibleDescription(/El texto tiene 501\/500 palabras/);
  });

  it("una imagen exige texto alternativo", async () => {
    renderEditor(
      context({
        kind: "image",
        body_md: null,
        media_id: "0b6a0366-9b56-451a-9a19-49cbcbe21c1c",
        alt_text: "",
      }),
    );
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Guardar cambios" }));

    expect(screen.getByLabelText("Texto alternativo")).toHaveAccessibleDescription(
      "Describe la imagen para quienes usan lector de pantalla.",
    );
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("edita las opciones compartidas de la A a la H con su retroalimentación", async () => {
    let created: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/content/contexts", async ({ request }) => {
        created = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          context({ code: "ING-CTX-1", module: "ING", kind: "shared_options", revision: 0 }),
          { status: 201, headers: { ETag: '"0"' } },
        );
      }),
    );
    renderEditor();
    const user = userEvent.setup();

    await screen.findByRole("option", { name: "Inglés" });
    await user.selectOptions(screen.getByLabelText("Módulo"), "ING");
    await user.type(screen.getByLabelText("Código"), "ING-CTX-1");
    await user.selectOptions(screen.getByLabelText("Tipo de contexto"), "shared_options");
    await user.type(screen.getByLabelText("Título"), "Avisos");
    await user.selectOptions(screen.getByLabelText("Parte"), "ing-p1");
    expect(screen.getByLabelText("Texto de la opción H")).toBeInTheDocument();
    for (const key of "ABCDEFGH") {
      await user.type(screen.getByLabelText(`Texto de la opción ${key}`), `Aviso ${key}`);
      await user.type(screen.getByLabelText(`Retroalimentación de la opción ${key}`), `Por ${key}`);
    }
    await user.click(screen.getByRole("button", { name: "Crear contexto" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Contexto creado.");
    expect(created).toMatchObject({ code: "ING-CTX-1", module: "ING", part_node_id: "ing-p1" });
    expect((created as unknown as { shared_options: unknown[] }).shared_options).toHaveLength(8);
  });
});
