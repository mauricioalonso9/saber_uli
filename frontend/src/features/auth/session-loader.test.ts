/** T067: estado de sesión para las guardias (caché, sin conexión y sesión inválida). */
import "fake-indexeddb/auto";

import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "@/api/model";
import { saveValidation } from "@/features/auth/offline-access";
import { createSessionLoader, loadSession } from "@/features/auth/session-loader";
import { useSessionStore } from "@/features/auth/session-store";
import { db } from "@/shared/db/dexie";

const ME = { id: "u1", onboarding: { consent_required: false, profile_required: false } } as Me;
const DAY = 24 * 60 * 60 * 1000;

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(async () => {
  useSessionStore.getState().clear();
  await db.meta.clear();
});
afterEach(() => {
  server.resetHandlers();
  vi.useRealTimers();
});
afterAll(() => server.close());

describe("loadSession", () => {
  it("con conexión y sesión válida queda autenticado", async () => {
    server.use(
      http.post("/api/auth/refresh", () =>
        HttpResponse.json({ access_token: "t", token_type: "Bearer", expires_in: 600 }),
      ),
      http.get("/api/v1/me", () => HttpResponse.json(ME)),
    );

    expect(await loadSession()).toEqual({ kind: "authenticated", me: ME });
  });

  it("con la sesión vencida queda anónimo", async () => {
    server.use(
      http.post("/api/auth/refresh", () =>
        HttpResponse.json(
          { type: "urn:saber-uli:problem:session-expired", title: "x", status: 401 },
          { status: 401 },
        ),
      ),
    );

    expect(await loadSession()).toEqual({ kind: "anonymous" });
  });

  it("sin red usa la instantánea de 7 días o menos", async () => {
    server.use(http.post("/api/auth/refresh", () => HttpResponse.error()));
    await saveValidation(ME, new Date(Date.now() - 2 * DAY));

    expect(await loadSession()).toEqual({ kind: "authenticated", me: ME });
  });

  it("sin red y con más de 7 días queda bloqueado", async () => {
    server.use(http.post("/api/auth/refresh", () => HttpResponse.error()));
    await saveValidation(ME, new Date(Date.now() - 8 * DAY));

    expect(await loadSession()).toEqual({ kind: "offline-expired" });
  });
});

describe("createSessionLoader", () => {
  it("carga una vez y vuelve a cargar tras invalidate()", async () => {
    const load = vi.fn(() => Promise.resolve({ kind: "anonymous" } as const));
    const get = createSessionLoader(load);

    await get();
    await get();
    expect(load).toHaveBeenCalledTimes(1);

    get.invalidate();
    await get();
    expect(load).toHaveBeenCalledTimes(2);
  });
});
