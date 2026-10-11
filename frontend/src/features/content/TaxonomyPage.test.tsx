/**
 * T104: mantenimiento de la taxonomía (US9; FR-001, FR-040, FR-045): árbol por módulo y tipo,
 * peso con el aviso de la suma, "Desactivar" en lugar de "Borrar" cuando está en uso, editor de
 * rúbricas y axe sin violaciones.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { ContentModule, TaxonomyNode } from "@/api/content/model";
import { useSessionStore } from "@/features/auth/session-store";
import { TaxonomyPage } from "@/features/content/TaxonomyPage";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

function node(code: string, kind: TaxonomyNode["kind"], extra: Partial<TaxonomyNode> = {}) {
  return {
    id: `id-${code}`,
    module: code.startsWith("ING") ? "ING" : "LC",
    kind,
    code,
    name: `Nombre de ${code}`,
    active: true,
    in_use: false,
    target_weight: null,
    parent_id: null,
    ...extra,
  } as TaxonomyNode;
}

const MODULES: ContentModule[] = [
  {
    code: "LC",
    name: "Lectura crítica",
    question_type: "selection",
    options_per_item: 4,
    max_context_words: 500,
    exam_questions: 35,
    bank_target: 150,
    nodes: [
      node("LC-C1", "competence", { in_use: true }),
      node("LC-A1", "assertion", { parent_id: "id-LC-C1", target_weight: 0.26, in_use: true }),
      node("LC-A2", "assertion", { parent_id: "id-LC-C1", target_weight: 0.4 }),
      node("LC-E1", "evidence", { parent_id: "id-LC-A1", in_use: true }),
      node("LC-E9", "evidence", { parent_id: "id-LC-A1", active: false }),
    ],
  },
  {
    code: "ING",
    name: "Inglés",
    question_type: "selection",
    options_per_item: null,
    max_context_words: null,
    exam_questions: 45,
    bank_target: 225,
    nodes: [node("ING-P2", "part", { target_weight: 0.11, part_options: 3 })],
  },
];

let requests: { method: string; url: string; body: unknown }[];

beforeEach(() => {
  useSessionStore.getState().setSession("token", 600);
  requests = [];
  const record = async (request: Request) => {
    requests.push({
      method: request.method,
      url: new URL(request.url).pathname,
      body: request.method === "DELETE" ? null : await request.json(),
    });
  };
  server.use(
    http.get("/api/v1/content/modules", () => HttpResponse.json({ items: MODULES })),
    http.get("/api/v1/content/rubrics", () => HttpResponse.json({ items: [] })),
    http.patch("/api/v1/content/taxonomy-nodes/:id", async ({ request }) => {
      await record(request);
      return HttpResponse.json({
        ...MODULES[0]!.nodes[1],
        target_weight: 0.3,
        warnings: ["Los pesos de las afirmaciones de LC suman 0,7; deberían sumar cerca de 1."],
      });
    }),
    http.delete("/api/v1/content/taxonomy-nodes/:id", async ({ request }) => {
      await record(request);
      return new HttpResponse(null, { status: 204 });
    }),
    http.patch("/api/v1/content/modules/:code", async ({ request }) => {
      await record(request);
      return HttpResponse.json({ ...MODULES[0], bank_target: 200 });
    }),
    http.post("/api/v1/content/rubrics", async ({ request }) => {
      await record(request);
      return HttpResponse.json(
        { id: "r-1", ...(requests.at(-1)!.body as object) },
        { status: 201 },
      );
    }),
  );
});

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <TaxonomyPage />
    </QueryClientProvider>,
  );
}

describe("taxonomía", () => {
  it("muestra el árbol del módulo por tipo, con las inactivas marcadas", async () => {
    renderPage();
    const user = userEvent.setup();

    const tree = await screen.findByRole("list", { name: "Categorías de Lectura crítica" });
    const competence = within(tree).getByRole("listitem", { name: /LC-C1/ });
    expect(within(competence).getByRole("listitem", { name: /LC-A1/ })).toBeInTheDocument();
    const evidence = within(competence).getByRole("listitem", { name: /LC-E9/ });
    expect(evidence).toHaveTextContent("Evidencia");
    expect(evidence).toHaveTextContent("Inactiva");

    await user.selectOptions(screen.getByLabelText("Módulo"), "ING");
    const ing = await screen.findByRole("list", { name: "Categorías de Inglés" });
    expect(within(ing).getByRole("listitem", { name: /ING-P2/ })).toHaveTextContent("Parte");
    expect(requests).toEqual([]);
  });

  it("edita el peso y muestra el aviso de la suma", async () => {
    renderPage();
    const user = userEvent.setup();

    const weight = await screen.findByLabelText("Peso de LC-A1");
    await user.clear(weight);
    await user.type(weight, "0,3");
    await user.click(screen.getByRole("button", { name: "Guardar LC-A1" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Los pesos de las afirmaciones de LC suman 0,7; deberían sumar cerca de 1.",
    );
    expect(requests).toEqual([
      {
        method: "PATCH",
        url: "/api/v1/content/taxonomy-nodes/id-LC-A1",
        body: { target_weight: 0.3 },
      },
    ]);
  });

  it("ofrece Desactivar y no Borrar a lo que está en uso", async () => {
    renderPage();
    const user = userEvent.setup();

    await screen.findByRole("list", { name: "Categorías de Lectura crítica" });
    expect(screen.getByRole("button", { name: "Desactivar LC-E1" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Borrar LC-E1" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reactivar LC-E9" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Borrar LC-A2" }));

    await screen.findByRole("status");
    expect(requests).toEqual([
      { method: "DELETE", url: "/api/v1/content/taxonomy-nodes/id-LC-A2", body: null },
    ]);
  });

  it("cambia la meta del módulo", async () => {
    renderPage();
    const user = userEvent.setup();

    const target = await screen.findByLabelText("Meta de ítems del módulo");
    expect(target).toHaveValue(150);
    await user.clear(target);
    await user.type(target, "200");
    await user.click(screen.getByRole("button", { name: "Guardar la meta" }));

    await screen.findByRole("status");
    expect(requests).toEqual([
      { method: "PATCH", url: "/api/v1/content/modules/LC", body: { bank_target: 200 } },
    ]);
  });

  it("crea una rúbrica con sus dimensiones y niveles", async () => {
    renderPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Nueva rúbrica" }));
    const form = screen.getByRole("form", { name: "Rúbrica" });
    await user.type(within(form).getByLabelText("Código"), "RUB-CE-09");
    await user.type(within(form).getByLabelText("Nombre"), "Texto argumentativo");
    await user.type(within(form).getByLabelText("Condición de pertinencia"), "Pertinencia");
    await user.type(within(form).getByLabelText("Qué exige la condición"), "Responde");
    await user.type(within(form).getByLabelText("Código de la dimensión 1"), "planteamiento");
    await user.type(within(form).getByLabelText("Nombre de la dimensión 1"), "Planteamiento");
    await user.type(
      within(form).getByLabelText("Niveles de la dimensión 1 (uno por línea)"),
      "Confusa{Enter}Clara",
    );
    await user.click(within(form).getByRole("button", { name: "Guardar la rúbrica" }));

    await screen.findByRole("status");
    expect(requests.at(-1)).toEqual({
      method: "POST",
      url: "/api/v1/content/rubrics",
      body: {
        code: "RUB-CE-09",
        name: "Texto argumentativo",
        note: null,
        active: true,
        relevance_condition: { name: "Pertinencia", description: "Responde" },
        dimensions: [
          {
            code: "planteamiento",
            name: "Planteamiento",
            levels: [
              { level: 1, description: "Confusa" },
              { level: 2, description: "Clara" },
            ],
          },
        ],
      },
    });
  });

  it("no tiene violaciones de axe", async () => {
    const { container } = renderPage();
    await screen.findByRole("list", { name: "Categorías de Lectura crítica" });

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });

    expect(result.violations).toEqual([]);
  });
});
