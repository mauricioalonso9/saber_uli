/**
 * T043: cola de revisión de los administradores (US2; FR-013, FR-019).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import type { ItemSummary } from "@/api/content/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";
import { ADMIN_CONTENT, summary, withPermissions } from "@/features/content/testing";

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
    http.get("/api/v1/content/items", ({ request }) => {
      const params = new URL(request.url).searchParams;
      queries.push(params);
      return HttpResponse.json({
        items,
        meta: { page: Number(params.get("page") ?? 1), page_size: 50, total },
      });
    }),
  );
}

function renderQueue() {
  useSessionStore.getState().setSession("token", 600);
  const router = createAppRouter({
    initialPath: "/banco/revision",
    getSession: createSessionLoader(() =>
      Promise.resolve({
        kind: "authenticated" as const,
        me: withPermissions("admin", ADMIN_CONTENT),
      }),
    ),
  });
  render(<App router={router} />);
}

describe("cola de revisión", () => {
  it("lista los ítems que puedo revisar, con su origen IA visible", async () => {
    serve([
      summary(),
      summary({ code: "RC-0001", module: "RC", origin: "teacher", assertion_code: "RC-A1" }),
    ]);
    renderQueue();

    const table = await screen.findByRole("table", { name: "Ítems por revisar" });
    const [, first, second] = within(table).getAllByRole("row");
    expect(first).toHaveTextContent("LC-0001");
    expect(first).toHaveTextContent("IA");
    expect(second).toHaveTextContent("RC-0001");
    expect(second).not.toHaveTextContent("IA");
    expect(within(first).getByRole("link", { name: "LC-0001" })).toHaveAttribute(
      "href",
      "/banco/items/LC-0001",
    );
    expect(queries[0].get("awaiting_my_review")).toBe("true");
  });

  it("filtra por módulo", async () => {
    serve([summary()]);
    renderQueue();
    const user = userEvent.setup();
    await screen.findByRole("table", { name: "Ítems por revisar" });

    await user.selectOptions(screen.getByLabelText("Módulo"), "RC");

    await expect.poll(() => queries.at(-1)?.get("module")).toBe("RC");
  });

  it("avisa cuando ningún otro administrador puede aprobar", async () => {
    serve([summary({ needs_another_reviewer: true })]);
    renderQueue();

    expect(await screen.findByText(/Necesita otro administrador/)).toBeInTheDocument();
  });

  it("sin ítems pendientes lo dice", async () => {
    serve([]);
    renderQueue();

    expect(await screen.findByText("No hay ítems por revisar.")).toBeInTheDocument();
  });

  it("pagina cuando hay más de 50 por revisar (T119)", async () => {
    serve([summary()], 120);
    renderQueue();
    const user = userEvent.setup();

    expect(await screen.findByText("Página 1 de 3 · 120 ítems")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    await expect.poll(() => queries.at(-1)?.get("page")).toBe("2");
    expect(queries.at(-1)?.get("awaiting_my_review")).toBe("true");
  });

  it("busca por código o texto (T119)", async () => {
    serve([summary()]);
    renderQueue();
    const user = userEvent.setup();
    await screen.findByRole("table", { name: "Ítems por revisar" });

    await user.type(screen.getByRole("searchbox", { name: "Buscar" }), "LC-0001");
    await user.click(screen.getByRole("button", { name: "Buscar" }));

    await expect.poll(() => queries.at(-1)?.get("q")).toBe("LC-0001");
    expect(queries.at(-1)?.get("page")).toBe("1");
  });
});
