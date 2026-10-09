/**
 * T062: sesión en memoria y cliente HTTP (research R-14 a R-17; FR-037 a FR-039).
 */
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import contract from "../../../../specs/001-identidad-acceso/contracts/openapi.yaml?raw";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem, customInstance, refreshAccessToken } from "@/shared/api/http";
import { GENERIC_MESSAGE, problemMessage } from "@/shared/api/problem-messages";

const PROBLEM = "urn:saber-uli:problem:";

function problem(status: number, slug: string) {
  return HttpResponse.json(
    { type: `${PROBLEM}${slug}`, title: slug, status },
    { status, headers: { "Content-Type": "application/problem+json" } },
  );
}

function tokens(accessToken: string) {
  return HttpResponse.json({ access_token: accessToken, token_type: "Bearer", expires_in: 600 });
}

const server = setupServer();
let refreshCalls: Request[] = [];

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  refreshCalls = [];
  useSessionStore.getState().clear();
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

/** /api/v1/me acepta solo `Bearer nuevo`; con otro token responde 401 `unauthenticated`. */
function meRequiresToken(valid: string) {
  return http.get("/api/v1/me", ({ request }) =>
    request.headers.get("Authorization") === `Bearer ${valid}`
      ? HttpResponse.json({ id: "u1" })
      : problem(401, "unauthenticated"),
  );
}

function refreshReturns(response: () => Response) {
  return http.post("/api/auth/refresh", ({ request }) => {
    refreshCalls.push(request.clone());
    return response();
  });
}

describe("token de acceso en memoria", () => {
  it("se guarda en el store y nunca en localStorage, sessionStorage ni IndexedDB", async () => {
    const openIndexedDb = vi.fn();
    vi.stubGlobal("indexedDB", { open: openIndexedDb });
    server.use(
      refreshReturns(() => tokens("nuevo")),
      meRequiresToken("nuevo"),
    );

    await refreshAccessToken();
    await customInstance("/api/v1/me");

    expect(useSessionStore.getState().accessToken).toBe("nuevo");
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(openIndexedDb).not.toHaveBeenCalled();
    expect("persist" in useSessionStore).toBe(false);
    vi.unstubAllGlobals();
  });

  it("calcula el vencimiento a partir de expires_in", async () => {
    vi.useFakeTimers({ now: new Date("2026-10-06T12:00:00Z"), toFake: ["Date"] });
    server.use(refreshReturns(() => tokens("nuevo")));

    await refreshAccessToken();

    expect(useSessionStore.getState().expiresAt).toBe(Date.parse("2026-10-06T12:10:00Z"));
    vi.useRealTimers();
  });

  it("clear() borra el token", () => {
    useSessionStore.getState().setSession("abc", 600);
    useSessionStore.getState().clear();

    expect(useSessionStore.getState().accessToken).toBeNull();
  });
});

describe("cliente HTTP", () => {
  it("envía Authorization con el token en memoria y X-Requested-With", async () => {
    let seen: Headers | undefined;
    server.use(
      http.get("/api/v1/me", ({ request }) => {
        seen = request.headers;
        return HttpResponse.json({ id: "u1" });
      }),
    );
    useSessionStore.getState().setSession("abc", 600);

    await expect(customInstance("/api/v1/me")).resolves.toEqual({ id: "u1" });
    expect(seen?.get("Authorization")).toBe("Bearer abc");
    expect(seen?.get("X-Requested-With")).toBe("saber-uli");
  });

  it("sin token no envía Authorization", async () => {
    let seen: Headers | undefined;
    server.use(
      http.get("/api/v1/policy/current", ({ request }) => {
        seen = request.headers;
        return HttpResponse.json({});
      }),
    );

    await customInstance("/api/v1/policy/current");
    expect(seen?.has("Authorization")).toBe(false);
  });

  it("devuelve undefined en 204", async () => {
    server.use(http.post("/api/auth/logout", () => new HttpResponse(null, { status: 204 })));

    await expect(customInstance("/api/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });

  it("la renovación envía X-Requested-With: saber-uli y la cookie del mismo origen", async () => {
    server.use(refreshReturns(() => tokens("nuevo")));

    await refreshAccessToken();

    expect(refreshCalls).toHaveLength(1);
    expect(refreshCalls[0]?.method).toBe("POST");
    expect(refreshCalls[0]?.headers.get("X-Requested-With")).toBe("saber-uli");
    expect(refreshCalls[0]?.credentials).toBe("same-origin");
  });
});

describe("ante 401", () => {
  it("renueva una sola vez y reintenta con el token nuevo", async () => {
    server.use(
      refreshReturns(() => tokens("nuevo")),
      meRequiresToken("nuevo"),
    );
    useSessionStore.getState().setSession("vencido", 600);

    await expect(customInstance("/api/v1/me")).resolves.toEqual({ id: "u1" });
    expect(refreshCalls).toHaveLength(1);
    expect(useSessionStore.getState().accessToken).toBe("nuevo");
  });

  it("varias peticiones concurrentes comparten una sola renovación", async () => {
    server.use(
      refreshReturns(() => tokens("nuevo")),
      meRequiresToken("nuevo"),
    );
    useSessionStore.getState().setSession("vencido", 600);

    await Promise.all([
      customInstance("/api/v1/me"),
      customInstance("/api/v1/me"),
      customInstance("/api/v1/me"),
    ]);
    expect(refreshCalls).toHaveLength(1);
  });

  it("si el reintento vuelve a dar 401 no renueva otra vez y lanza el problema", async () => {
    server.use(
      refreshReturns(() => tokens("nuevo")),
      meRequiresToken("otro"),
    );
    useSessionStore.getState().setSession("vencido", 600);

    const error = await customInstance("/api/v1/me").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiProblem);
    expect((error as ApiProblem).slug).toBe("unauthenticated");
    expect(refreshCalls).toHaveLength(1);
  });

  it("si la renovación falla borra la sesión y lanza la causa de la renovación", async () => {
    server.use(
      refreshReturns(() => problem(401, "account-disabled")),
      meRequiresToken("nuevo"),
    );
    useSessionStore.getState().setSession("vencido", 600);

    const error = await customInstance("/api/v1/me").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiProblem);
    expect((error as ApiProblem).slug).toBe("account-disabled");
    expect((error as ApiProblem).message).toBe(problemMessage(`${PROBLEM}account-disabled`, 401));
    expect(useSessionStore.getState().accessToken).toBeNull();
  });

  it("reauthentication-required no intenta renovar (R-15)", async () => {
    server.use(
      refreshReturns(() => tokens("nuevo")),
      http.get("/api/v1/admin/users", () => problem(401, "reauthentication-required")),
    );
    useSessionStore.getState().setSession("abc", 600);

    const error = await customInstance("/api/v1/admin/users").catch((e: unknown) => e);
    expect((error as ApiProblem).slug).toBe("reauthentication-required");
    expect(refreshCalls).toHaveLength(0);
    expect(useSessionStore.getState().accessToken).toBe("abc");
  });

  it("las rutas /api/auth/ no disparan renovación", async () => {
    server.use(
      refreshReturns(() => tokens("nuevo")),
      http.post("/api/auth/guest/sessions", () => problem(401, "access-link-invalid")),
    );

    const error = await customInstance("/api/auth/guest/sessions", { method: "POST" }).catch(
      (e: unknown) => e,
    );
    expect((error as ApiProblem).slug).toBe("access-link-invalid");
    expect(refreshCalls).toHaveLength(0);
  });
});

describe("errores", () => {
  it("convierte un problema RFC 9457 en ApiProblem con mensaje en español", async () => {
    server.use(
      http.post("/api/v1/invitations", () =>
        HttpResponse.json(
          {
            type: `${PROBLEM}validation-error`,
            title: "Datos inválidos",
            status: 422,
            errors: [{ field: "email", message: "Correo inválido" }],
          },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );

    const error = (await customInstance("/api/v1/invitations", { method: "POST" }).catch(
      (e: unknown) => e,
    )) as ApiProblem;
    expect(error.status).toBe(422);
    expect(error.type).toBe(`${PROBLEM}validation-error`);
    expect(error.slug).toBe("validation-error");
    expect(error.errors).toEqual([{ field: "email", message: "Correo inválido" }]);
    expect(error.message).toBe(problemMessage(`${PROBLEM}validation-error`, 422));
  });

  it("una respuesta que no es JSON produce un mensaje según el estado", async () => {
    server.use(
      http.get("/api/v1/me", () => new HttpResponse("<html>Bad gateway</html>", { status: 502 })),
    );
    useSessionStore.getState().setSession("abc", 600);

    const error = (await customInstance("/api/v1/me").catch((e: unknown) => e)) as ApiProblem;
    expect(error.status).toBe(502);
    expect(error.slug).toBe("service-unavailable");
  });

  it("un fallo de red produce el problema network-error", async () => {
    server.use(http.get("/api/v1/me", () => HttpResponse.error()));

    const error = (await customInstance("/api/v1/me").catch((e: unknown) => e)) as ApiProblem;
    expect(error).toBeInstanceOf(ApiProblem);
    expect(error.status).toBe(0);
    expect(error.slug).toBe("network-error");
  });
});

describe("mensajes de problema", () => {
  // Todos los `type` del contrato: los que aparecen como `slug-con-guiones` en las descripciones
  // y los de una sola palabra de las respuestas comunes.
  const contractSlugs = [
    ...new Set([
      ...[...contract.matchAll(/`([a-z]+(?:-[a-z0-9]+)+)`/g)].map((m) => m[1] as string),
      "unauthenticated",
      "forbidden",
      "conflict",
    ]),
  ].sort();

  it("el catálogo del contrato no está vacío", () => {
    expect(contractSlugs.length).toBeGreaterThan(25);
  });

  it.each(contractSlugs)("traduce %s a un mensaje propio en español", (slug) => {
    const message = problemMessage(`${PROBLEM}${slug}`, 400);
    expect(message).not.toBe(GENERIC_MESSAGE);
    expect(message).not.toContain(slug);
    expect(message).toMatch(/[a-záéíóúñ]/);
  });

  it.each([
    [429, "rate-limited"],
    [503, "service-unavailable"],
    [500, "service-unavailable"],
  ])("un tipo desconocido con estado %i usa el mensaje de %s", (status, slug) => {
    expect(problemMessage("about:blank", status)).toBe(problemMessage(`${PROBLEM}${slug}`, status));
  });

  it("un tipo desconocido sin estado específico usa el mensaje genérico", () => {
    expect(problemMessage(`${PROBLEM}algo-nuevo`, 400)).toBe(GENERIC_MESSAGE);
  });
});
