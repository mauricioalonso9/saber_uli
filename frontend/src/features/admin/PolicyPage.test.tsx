/**
 * T092: publicar una versión de la política (FR-017): vista previa, validación de versión y
 * longitud, y errores del servidor.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Me, PolicyVersion, PublishPolicyVersionBody } from "@/api/model";
import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";
import { createSessionLoader } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";

const CURRENT: PolicyVersion = {
  id: "0192f3c4-0000-7000-8000-0000000000a1",
  version: "1.0",
  title: "Política de tratamiento de datos personales de Saber Uli",
  effective_from: "2026-10-01T05:00:00Z",
  body_markdown: "# Política\n\nTexto.",
};

const ADMIN: Me = {
  id: "0192f3c4-0000-7000-8000-000000000001",
  kind: "institutional",
  status: "active",
  display_name: "Admin",
  email: "admin@unilibre.edu.co",
  roles: ["admin", "student"],
  permissions: ["policy:publish"],
  onboarding: { consent_required: false, profile_required: false },
  access: {
    valid: true,
    validated_at: "2026-10-07T12:00:00Z",
    offline_grace_until: "2026-10-14T12:00:00Z",
    privileged_session: true,
  },
};

const BODY = `## Finalidades\n\n${"Usamos sus datos para medir su progreso. ".repeat(6)}`;

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

let published: PublishPolicyVersionBody[];

function renderPolicyPage() {
  published = [];
  server.use(
    http.get("/api/v1/privacy-policy/current", () => HttpResponse.json(CURRENT)),
    http.post("/api/v1/admin/privacy-policy/versions", async ({ request }) => {
      const body = (await request.json()) as PublishPolicyVersionBody;
      published.push(body);
      return HttpResponse.json(
        { ...body, id: "0192f3c4-0000-7000-8000-0000000000a2" },
        {
          status: 201,
        },
      );
    }),
  );
  const router = createAppRouter({
    initialPath: "/admin/politica",
    getSession: createSessionLoader(() =>
      Promise.resolve({ kind: "authenticated" as const, me: ADMIN }),
    ),
  });
  render(<App router={router} />);
}

async function fill(values: { version?: string; title?: string; body?: string }) {
  const user = userEvent.setup();
  await screen.findByLabelText("Título");
  if (values.version !== undefined) {
    await user.clear(screen.getByLabelText("Número de versión"));
    if (values.version) await user.type(screen.getByLabelText("Número de versión"), values.version);
  }
  if (values.title !== undefined) {
    await user.clear(screen.getByLabelText("Título"));
    if (values.title) await user.type(screen.getByLabelText("Título"), values.title);
  }
  if (values.body !== undefined) {
    await user.clear(screen.getByLabelText("Texto de la política (Markdown)"));
    if (values.body) {
      // `paste` evita escribir cientos de caracteres uno por uno.
      await user.click(screen.getByLabelText("Texto de la política (Markdown)"));
      await user.paste(values.body);
    }
  }
  return user;
}

function failWith(status: number, slug: string) {
  server.use(
    http.post("/api/v1/admin/privacy-policy/versions", () =>
      HttpResponse.json(
        { type: `urn:saber-uli:problem:${slug}`, title: "Error", status },
        { status, headers: { "Content-Type": "application/problem+json" } },
      ),
    ),
  );
}

describe("publicar una versión de la política", () => {
  it("muestra la versión vigente", async () => {
    renderPolicyPage();

    expect(await screen.findByText(/versión vigente: 1\.0/i)).toBeInTheDocument();
  });

  it("valida el formato de la versión y la longitud del texto sin enviar nada", async () => {
    renderPolicyPage();
    const user = await fill({ version: "v2", title: "Política", body: "Muy corto." });

    await user.click(screen.getByRole("button", { name: "Publicar versión" }));

    expect(await screen.findByText(/formato número\.número/i)).toBeInTheDocument();
    expect(screen.getByText(/al menos 200 caracteres/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Número de versión")).toHaveAttribute("aria-invalid", "true");
    expect(published).toEqual([]);
  });

  it("la vista previa muestra el Markdown sin interpretar HTML", async () => {
    renderPolicyPage();
    const user = await fill({ title: "Política 2.0", body: `${BODY}\n\n<img src=x>` });

    await user.click(screen.getByRole("button", { name: "Vista previa" }));

    const preview = await screen.findByRole("article", { name: "Política 2.0" });
    expect(preview).toContainElement(screen.getByRole("heading", { name: "Finalidades" }));
    expect(preview.querySelector("img")).toBeNull();
  });

  it("publica con la fecha de vigencia en hora de Colombia y confirma", async () => {
    renderPolicyPage();
    const user = await fill({ version: "2.0", title: "Política 2.0", body: BODY });

    await user.click(screen.getByRole("button", { name: "Publicar versión" }));

    expect(await screen.findByText(/publicaste la versión 2\.0/i)).toHaveAttribute(
      "role",
      "status",
    );
    expect(published).toHaveLength(1);
    const [body] = published;
    expect(body).toMatchObject({ version: "2.0", title: "Política 2.0", body_markdown: BODY });
    expect(body?.effective_from).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-05:00$/);
  });

  it.each([
    [409, "policy-version-exists", /ya fue publicada/i],
    [401, "reauthentication-required", /confirma tu identidad/i],
  ])("muestra el error %i (%s)", async (status, slug, message) => {
    renderPolicyPage();
    failWith(status, slug);
    const user = await fill({ version: "1.0", title: "Política", body: BODY });

    await user.click(screen.getByRole("button", { name: "Publicar versión" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });
});
