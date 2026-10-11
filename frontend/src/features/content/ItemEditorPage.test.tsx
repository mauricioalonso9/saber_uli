/**
 * T054: editor de ítems (US3; FR-015, FR-016, FR-024, FR-025, FR-027).
 *
 * Los campos dependen del módulo y de la parte; los errores del cliente (las mismas reglas del
 * servidor, `schemas.ts`) y del servidor aparecen junto al campo y se anuncian; sobre un ítem
 * publicado avisa que se creará una versión nueva. El conflicto (412) lo cubre
 * `EditConflictDialog.test.tsx` y la vista previa, `ItemPreview.test.tsx`.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Item } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { ItemEditor } from "@/features/content/ItemEditorPage";
import { item, MODULES, RUBRICS, version } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => {
  useSessionStore.getState().setSession("token", 600);
  server.use(
    http.get("/api/v1/content/modules", () => HttpResponse.json({ items: MODULES })),
    http.get("/api/v1/content/rubrics", () => HttpResponse.json({ items: RUBRICS })),
  );
});
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

function renderEditor(value?: Item) {
  const onSaved = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ItemEditor item={value} onSaved={onSaved} />
    </QueryClientProvider>,
  );
  return onSaved;
}

function lcDraft(): Item {
  return item({
    code: "LC-0301",
    origin: "teacher",
    revision: 2,
    open: version({
      state: "draft",
      content: {
        ...version().content,
        taxonomy: {
          competence_id: "lc-c1",
          assertion_id: "lc-a1",
          evidence_id: "lc-e1",
          component_id: null,
          situation_id: null,
          part_id: null,
        },
      },
    }),
  });
}

describe("editor de ítems", () => {
  it("los campos cambian según el módulo y la parte", async () => {
    renderEditor();
    const user = userEvent.setup();

    await screen.findByRole("option", { name: "Lectura crítica" });
    await user.selectOptions(screen.getByLabelText("Módulo"), "LC");
    expect(screen.getByLabelText("Afirmación")).toBeInTheDocument();
    expect(screen.getByLabelText("Texto de la opción A")).toBeInTheDocument();
    expect(screen.queryByLabelText("Texto de la opción E")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Módulo"), "ING");
    expect(screen.queryByLabelText("Afirmación")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Parte"), "ing-p2");
    expect(screen.getByLabelText("Texto de la opción C")).toBeInTheDocument();
    expect(screen.queryByLabelText("Texto de la opción D")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Parte"), "ing-p1");
    expect(screen.queryByLabelText("Texto de la opción A")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Clave correcta (entre las opciones del contexto)")).toBeVisible();

    await user.selectOptions(screen.getByLabelText("Módulo"), "CE");
    expect(await screen.findByLabelText("Rúbrica")).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: "Texto argumentativo" })).toBeInTheDocument();
    expect(screen.getByLabelText("Contexto de la consigna")).toBeInTheDocument();
    expect(screen.queryByLabelText("Explicación general")).not.toBeInTheDocument();
  });

  it("los errores del cliente aparecen junto al campo y se anuncian", async () => {
    let posted = false;
    server.use(
      http.put("/api/v1/content/items/:code/draft", () => {
        posted = true;
        return HttpResponse.json(lcDraft());
      }),
    );
    renderEditor(lcDraft());
    const user = userEvent.setup();

    await user.clear(await screen.findByLabelText("Retroalimentación de la opción B"));
    await user.clear(screen.getByLabelText("Explicación general"));
    await user.click(screen.getByRole("button", { name: "Enviar a revisión" }));

    const feedback = screen.getByLabelText("Retroalimentación de la opción B");
    expect(feedback).toHaveAttribute("aria-invalid", "true");
    expect(feedback).toHaveAccessibleDescription("La opción B necesita su retroalimentación.");
    expect(screen.getByLabelText("Explicación general")).toHaveAccessibleDescription(
      "Escribe la explicación general.",
    );
    expect(screen.getByRole("status")).toHaveTextContent("Revisa los 2 campos marcados.");
    expect(posted).toBe(false);
  });

  it("los errores del servidor también aparecen junto al campo", async () => {
    server.use(
      http.put("/api/v1/content/items/:code/draft", () =>
        HttpResponse.json(
          {
            type: "urn:saber-uli:problem:duplicate-item",
            title: "x",
            status: 409,
            detail: "El contenido coincide con el ítem LC-0007.",
          },
          { status: 409, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
      http.post("/api/v1/content/items/:code/submission", () =>
        HttpResponse.json(
          {
            type: "urn:saber-uli:problem:validation-error",
            title: "x",
            status: 422,
            errors: [
              {
                field: "taxonomy.assertion_id",
                rule: "taxonomy_inactive",
                message: "La afirmación LC-A1 está desactivada.",
              },
            ],
          },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    renderEditor(lcDraft());
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Guardar borrador" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("LC-0007");

    server.use(
      http.put("/api/v1/content/items/:code/draft", () =>
        HttpResponse.json(lcDraft(), { headers: { ETag: '"2"' } }),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Enviar a revisión" }));

    expect(await screen.findByLabelText("Afirmación")).toHaveAccessibleDescription(
      "La afirmación LC-A1 está desactivada.",
    );
    expect(screen.getByRole("status")).toHaveTextContent("Revisa el campo marcado.");
  });

  it("guarda con If-Match y avisa la versión nueva sobre un ítem publicado", async () => {
    const published = item({
      code: "LC-0301",
      revision: 5,
      published: version({ state: "published", number: 1 }),
      open: null,
    });
    const calls: { ifMatch: string | null; keep: string | null; body: unknown }[] = [];
    server.use(
      http.put("/api/v1/content/items/:code/draft", async ({ request }) => {
        calls.push({
          ifMatch: request.headers.get("If-Match"),
          keep: new URL(request.url).searchParams.get("keep_in_review"),
          body: await request.json(),
        });
        return HttpResponse.json(
          item({ ...published, revision: 6, open: version({ state: "draft", number: 2 }) }),
          { headers: { ETag: '"6"' } },
        );
      }),
    );
    const onSaved = renderEditor(published);
    const user = userEvent.setup();

    expect(
      await screen.findByText(/Este ítem está publicado: al guardar se creará la versión 2/),
    ).toBeInTheDocument();
    const stem = await screen.findByLabelText("Enunciado");
    await user.clear(stem);
    await user.type(stem, "Nuevo enunciado");
    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Cambios guardados.");
    expect(calls).toHaveLength(1);
    expect(calls[0].ifMatch).toBe('"5"');
    expect(calls[0].keep).toBeNull();
    expect(calls[0].body).toMatchObject({ stem_md: "Nuevo enunciado" });
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ revision: 6 }));
  });

  it("sobre una versión En revisión ofrece mantenerla en revisión", async () => {
    const inReview = item({ code: "LC-0301", revision: 3, open: version({ state: "in_review" }) });
    let keep: string | null = null;
    server.use(
      http.put("/api/v1/content/items/:code/draft", ({ request }) => {
        keep = new URL(request.url).searchParams.get("keep_in_review");
        return HttpResponse.json(inReview, { headers: { ETag: '"4"' } });
      }),
    );
    renderEditor(inReview);
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("checkbox", { name: /Mantener en revisión \(cambio menor\)/ }),
    );
    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await screen.findByText("Cambios guardados.");
    expect(keep).toBe("true");
  });

  it("crea un ítem nuevo y lo envía a revisión", async () => {
    const created = { ...lcDraft(), revision: 0 };
    const requests: string[] = [];
    server.use(
      http.post("/api/v1/content/items", async ({ request }) => {
        requests.push(`POST ${((await request.json()) as { code: string }).code}`);
        return HttpResponse.json(created, { status: 201, headers: { ETag: '"0"' } });
      }),
      http.post("/api/v1/content/items/:code/submission", ({ request }) => {
        requests.push(`submit ${request.headers.get("If-Match")}`);
        return HttpResponse.json(item({ ...created, revision: 1 }), { headers: { ETag: '"1"' } });
      }),
    );
    renderEditor();
    const user = userEvent.setup();

    await screen.findByRole("option", { name: "Lectura crítica" });
    await user.selectOptions(screen.getByLabelText("Módulo"), "LC");
    await user.type(screen.getByLabelText("Código"), "LC-0301");
    await user.selectOptions(screen.getByLabelText("Competencia"), "lc-c1");
    await user.selectOptions(screen.getByLabelText("Afirmación"), "lc-a1");
    await user.selectOptions(screen.getByLabelText("Evidencia"), "lc-e1");
    await user.type(screen.getByLabelText("Enunciado"), "¿Cuál es la tesis?");
    for (const key of "ABCD") {
      await user.type(screen.getByLabelText(`Texto de la opción ${key}`), `Opción ${key}`);
      await user.type(screen.getByLabelText(`Retroalimentación de la opción ${key}`), `Por ${key}`);
    }
    await user.click(screen.getByRole("radio", { name: "La opción A es la correcta" }));
    await user.type(screen.getByLabelText("Explicación general"), "Está en el texto.");
    await user.click(screen.getByRole("button", { name: "Enviar a revisión" }));

    expect(await screen.findByText("El ítem quedó en revisión.")).toBeInTheDocument();
    expect(requests).toEqual(["POST LC-0301", 'submit "0"']);
  });

  it("cada categoría se muestra con su código y su nombre", async () => {
    renderEditor();
    const user = userEvent.setup();

    await screen.findByRole("option", { name: "Lectura crítica" });
    await user.selectOptions(screen.getByLabelText("Módulo"), "LC");
    const assertions = within(screen.getByLabelText("Afirmación")).getAllByRole("option");

    expect(assertions.map((o) => o.textContent)).toEqual([
      "Elige…",
      "LC-A1 · Identifica contenidos",
      "LC-A2 · Comprende la estructura",
    ]);
  });
});
