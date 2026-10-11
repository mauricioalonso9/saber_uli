/**
 * T118: lista del banco (fase 13; FR-039, FR-043, SC-009, B1): tabla, búsqueda, filtros en la URL,
 * filtro de señales, paginación y axe.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { ItemSummary } from "@/api/content/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";
import { MODULES, summary, TEACHER_CONTENT, withPermissions } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let queries: URLSearchParams[];

function serve(items: ItemSummary[], total = items.length) {
  queries = [];
  server.use(
    http.get("/api/v1/content/modules", () => HttpResponse.json({ items: MODULES })),
    http.get("/api/v1/content/items", ({ request }) => {
      const params = new URL(request.url).searchParams;
      queries.push(params);
      return HttpResponse.json({
        items,
        meta: {
          page: Number(params.get("page") ?? 1),
          page_size: Number(params.get("page_size") ?? 25),
          total,
        },
      });
    }),
  );
}

function renderBank(path = "/banco") {
  useSessionStore.getState().setSession("token", 600);
  const router = createAppRouter({
    initialPath: path,
    getSession: createSessionLoader(() =>
      Promise.resolve({
        kind: "authenticated" as const,
        me: withPermissions("teacher", TEACHER_CONTENT),
      }),
    ),
  });
  const view = render(<App router={router} />);
  return { router, container: view.container };
}

const last = () => Object.fromEntries(queries.at(-1)!);

describe("lista del banco", () => {
  it("muestra cada ítem con su estado, origen, dificultad y señales en texto", async () => {
    serve([
      summary({
        code: "LC-0001",
        published_version: 1,
        open_version: { number: 2, state: "draft" },
        signals: ["too_hard", "distractor_beats_key"],
      }),
      summary({ code: "RC-0002", module: "RC", origin: "teacher", difficulty: "high" }),
      summary({ code: "CC-0003", module: "CC", retired: true, open_version: null }),
    ]);
    renderBank();

    const table = await screen.findByRole("table", { name: "Ítems del banco" });
    const [header, first, second, third] = within(table).getAllByRole("row");
    expect(header).toHaveTextContent(
      "CódigoMóduloEstadoOrigenDificultadEnunciadoSeñales de problema",
    );
    expect(within(first!).getByRole("link", { name: "LC-0001" })).toHaveAttribute(
      "href",
      "/banco/items/LC-0001",
    );
    expect(first).toHaveTextContent("Publicado (v1) · Borrador (v2)");
    expect(first).toHaveTextContent("Muy difícil, Una opción incorrecta supera a la correcta");
    expect(second).toHaveTextContent("Razonamiento cuantitativo");
    expect(second).toHaveTextContent("En revisión (v1)");
    expect(second).toHaveTextContent("Docente");
    expect(second).toHaveTextContent("Alta");
    expect(third).toHaveTextContent("Retirado");
  });

  it("toma los filtros de la URL, como el enlace de la cobertura", async () => {
    serve([summary()]);
    renderBank("/banco?module=LC&taxonomy_node=lc-a1");

    await screen.findByRole("table", { name: "Ítems del banco" });
    expect(last()).toEqual({ module: "LC", taxonomy_node: "lc-a1", page: "1", page_size: "25" });
    expect(screen.getByLabelText("Módulo")).toHaveValue("LC");
    expect(await screen.findByLabelText("Categoría")).toHaveValue("lc-a1");
  });

  it("filtra por señal de problema y busca, y lo guarda en la URL", async () => {
    serve([summary()]);
    const { router } = renderBank();
    const user = userEvent.setup();
    await screen.findByRole("table", { name: "Ítems del banco" });

    await user.selectOptions(screen.getByLabelText("Señal de problema"), "too_hard");
    await vi.waitFor(() => expect(last()).toMatchObject({ signal: "too_hard", page: "1" }));
    await user.type(screen.getByRole("searchbox", { name: "Buscar" }), "lectura");
    await user.click(screen.getByRole("button", { name: "Buscar" }));

    await vi.waitFor(() =>
      expect(last()).toMatchObject({ signal: "too_hard", q: "lectura", page: "1" }),
    );
    expect(router.state.location.search).toMatchObject({ signal: "too_hard", q: "lectura" });
  });

  it("pagina con el total", async () => {
    serve([summary()], 60);
    renderBank();
    const user = userEvent.setup();

    expect(await screen.findByText("Página 1 de 3 · 60 ítems")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    await vi.waitFor(() => expect(last()).toMatchObject({ page: "2" }));
    expect(await screen.findByText("Página 2 de 3 · 60 ítems")).toBeInTheDocument();
  });

  it("sin resultados lo dice", async () => {
    serve([]);
    renderBank("/banco?q=nada");

    expect(await screen.findByText("No hay ítems con esos filtros.")).toBeInTheDocument();
  });

  it("no tiene violaciones de axe", async () => {
    serve([summary({ signals: ["too_easy"] })]);
    const { container } = renderBank();
    await screen.findByRole("table", { name: "Ítems del banco" });

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });

    expect(result.violations).toEqual([]);
  });
});
