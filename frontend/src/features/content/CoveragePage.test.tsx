/**
 * T092: cobertura del banco (US7; FR-039): tabla por categoría con "Faltan N" en texto, orden por
 * faltantes, enlaces al banco filtrado y sin violaciones de axe.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import type { ModuleCoverage } from "@/api/content/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";
import { MODULES, TEACHER_CONTENT, withPermissions } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

function category(
  code: string,
  overrides: Partial<ModuleCoverage["categories"][number]> = {},
): ModuleCoverage["categories"][number] {
  return {
    node_id: `id-${code}`,
    code,
    name: `Nombre de ${code}`,
    target_weight: 0.3,
    published: 0,
    in_review: 0,
    published_share: 0,
    missing: 0,
    below_target: false,
    ...overrides,
  };
}

const LC: ModuleCoverage = {
  module: "LC",
  grouped_by: "assertion",
  bank_target: 150,
  published_total: 50,
  in_review_total: 7,
  categories: [
    category("LC-A1", {
      target_weight: 0.26,
      published: 40,
      in_review: 2,
      published_share: 0.8,
      missing: 0,
    }),
    category("LC-A2", {
      target_weight: 0.4,
      published: 10,
      in_review: 5,
      published_share: 0.2,
      missing: 50,
      below_target: true,
    }),
    category("LC-A3", { target_weight: 0.34, missing: 51, below_target: true }),
  ],
};

const CE: ModuleCoverage = {
  module: "CE",
  grouped_by: "competence",
  bank_target: 20,
  published_total: 1,
  in_review_total: 2,
  categories: [],
};

function renderCoverage() {
  const requested: string[] = [];
  server.use(
    http.get("/api/v1/content/modules", () => HttpResponse.json({ items: MODULES })),
    http.get("/api/v1/content/coverage/:module", ({ params }) => {
      requested.push(String(params.module));
      return HttpResponse.json(params.module === "CE" ? CE : LC);
    }),
  );
  useSessionStore.getState().setSession("token", 600);
  const router = createAppRouter({
    initialPath: "/banco/cobertura",
    getSession: createSessionLoader(() =>
      Promise.resolve({
        kind: "authenticated" as const,
        me: withPermissions("teacher", TEACHER_CONTENT),
      }),
    ),
  });
  const view = render(<App router={router} />);
  return { requested, container: view.container };
}

describe("cobertura del banco", () => {
  it("muestra cada categoría con Faltan N en texto, de la que más falta a la que menos", async () => {
    renderCoverage();

    const table = await screen.findByRole("table", { name: "Cobertura de Lectura crítica" });
    const [header, first, second, third] = within(table).getAllByRole("row");
    expect(header).toHaveTextContent(
      "CategoríaPublicadosEn revisiónPorcentaje realPorcentaje objetivoEstado",
    );
    expect(first).toHaveTextContent("LC-A3");
    expect(first).toHaveTextContent("Faltan 51");
    expect(second).toHaveTextContent("LC-A2");
    expect(second).toHaveTextContent(/10520\s?%40\s?%Faltan 50/u);
    expect(third).toHaveTextContent("LC-A1");
    expect(third).toHaveTextContent("Cumple el objetivo");
    expect(screen.getByText(/Meta del banco: 150 ítems/)).toBeInTheDocument();
    expect(screen.getByText(/50 publicados y 7 en revisión/)).toBeInTheDocument();
  });

  it("cada categoría enlaza al banco filtrado por ella", async () => {
    renderCoverage();

    const link = await screen.findByRole("link", { name: /LC-A2/ });

    expect(link.getAttribute("href")).toBe("/banco?module=LC&taxonomy_node=id-LC-A2");
  });

  it("cambia de módulo; sin pesos muestra solo los totales", async () => {
    const { requested } = renderCoverage();
    const user = userEvent.setup();
    await screen.findByRole("table", { name: "Cobertura de Lectura crítica" });

    await user.selectOptions(screen.getByLabelText("Módulo"), "CE");

    expect(await screen.findByText(/1 publicados y 2 en revisión/)).toBeInTheDocument();
    expect(screen.getByText(/Este módulo no tiene distribución objetivo/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(requested).toEqual(["LC", "CE"]);
  });

  it("no tiene violaciones de axe", async () => {
    const { container } = renderCoverage();
    await screen.findByRole("table", { name: "Cobertura de Lectura crítica" });

    const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });

    expect(result.violations).toEqual([]);
  });
});
