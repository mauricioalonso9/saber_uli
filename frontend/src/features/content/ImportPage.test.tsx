/**
 * T070: subir un archivo para importar y descargar la plantilla (US4; FR-028, FR-037).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";
import { importDetail, TEACHER_CONTENT, withPermissions } from "@/features/content/testing";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => {
  useSessionStore.getState().setSession("token", 600);
  server.use(
    http.get("/api/v1/content/imports", () =>
      HttpResponse.json({
        items: [importDetail({ source_name: "anterior.xlsx", status: "confirmed" })],
        meta: { page: 1, page_size: 25, total: 1 },
      }),
    ),
    http.get("/api/v1/content/imports/:id", () => HttpResponse.json(importDetail())),
  );
});
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const LABEL = "Archivo (.json del banco o .xlsx de la plantilla, hasta 10 MB)";

function renderUpload() {
  const router = createAppRouter({
    initialPath: "/banco/importar",
    getSession: createSessionLoader(() =>
      Promise.resolve({
        kind: "authenticated" as const,
        me: withPermissions("teacher", TEACHER_CONTENT),
      }),
    ),
  });
  render(<App router={router} />);
}

describe("importar ítems", () => {
  it("sube el archivo y muestra la vista previa con los conteos", async () => {
    let received: string | null = null;
    server.use(
      http.post("/api/v1/content/imports", ({ request }) => {
        // Leer el cuerpo multipart se cuelga con el File de jsdom; basta con el tipo.
        received = request.headers.get("Content-Type");
        return HttpResponse.json(importDetail(), { status: 201 });
      }),
    );
    renderUpload();
    const user = userEvent.setup();

    await user.upload(
      await screen.findByLabelText(LABEL),
      new File(['{"esquema_version":"1.0"}'], "banco.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Validar el archivo" }));

    const counts = await screen.findByRole("list", { name: "Resultado de la validación" });
    expect(within(counts).getByText("Nuevos: 2")).toBeInTheDocument();
    expect(received).toMatch(/^multipart\/form-data/);
  });

  it("explica por qué se rechazó el archivo", async () => {
    server.use(
      http.post("/api/v1/content/imports", () =>
        HttpResponse.json(
          { type: "urn:saber-uli:problem:batch-too-large", title: "x", status: 413 },
          { status: 413, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    renderUpload();
    const user = userEvent.setup();

    await user.upload(await screen.findByLabelText(LABEL), new File(["{}"], "banco.json"));
    await user.click(screen.getByRole("button", { name: "Validar el archivo" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/demasiadas filas/);
  });

  it("descarga la plantilla y lista las importaciones recientes", async () => {
    let downloaded = false;
    server.use(
      http.get("/api/v1/content/import-template", () => {
        downloaded = true;
        return new HttpResponse(new Uint8Array([80, 75]), {
          headers: {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          },
        });
      }),
    );
    renderUpload();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Descargar la plantilla" }));

    await vi.waitFor(() => expect(downloaded).toBe(true));
    const recent = await screen.findByRole("table", { name: "Importaciones recientes" });
    expect(within(recent).getByText("anterior.xlsx")).toBeInTheDocument();
  });
});
