/**
 * T064: acceso sin conexión (FR-038, FR-039; research R-17).
 */
import "fake-indexeddb/auto";

import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Me } from "@/api/model";
import {
  OFFLINE_GRACE_MS,
  evaluateOfflineAccess,
  revalidate,
  saveValidation,
  useCanSync,
} from "@/features/auth/offline-access";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem } from "@/shared/api/http";
import { db } from "@/shared/db/dexie";

const NOW = new Date("2026-10-06T12:00:00Z");
const DAY = 24 * 60 * 60 * 1000;

const ME: Me = {
  id: "0192f3c4-0000-7000-8000-000000000001",
  kind: "institutional",
  status: "active",
  display_name: "Ana",
  email: "ana@unilibre.edu.co",
  roles: ["student"],
  permissions: [],
  onboarding: { consent_required: false, profile_required: false },
  access: {
    valid: true,
    validated_at: NOW.toISOString(),
    offline_grace_until: new Date(NOW.getTime() + 7 * DAY).toISOString(),
  },
};

const server = setupServer();
let calls: string[] = [];

function api(refreshStatus = 200) {
  server.use(
    http.post("/api/auth/refresh", () => {
      calls.push("refresh");
      return refreshStatus === 200
        ? HttpResponse.json({ access_token: "nuevo", token_type: "Bearer", expires_in: 600 })
        : HttpResponse.json(
            {
              type: "urn:saber-uli:problem:session-expired",
              title: "Sesión vencida",
              status: refreshStatus,
            },
            { status: refreshStatus, headers: { "Content-Type": "application/problem+json" } },
          );
    }),
    http.get("/api/v1/me", ({ request }) => {
      calls.push(`me:${request.headers.get("Authorization") ?? ""}`);
      return HttpResponse.json(ME);
    }),
  );
}

function setOnline(online: boolean) {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(online);
  act(() => {
    window.dispatchEvent(new Event(online ? "online" : "offline"));
  });
}

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(async () => {
  calls = [];
  useSessionStore.getState().clear();
  await db.meta.clear();
});
afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
});
afterAll(() => server.close());

describe("instantánea en Dexie", () => {
  it("guarda /me y lastValidatedAt", async () => {
    await saveValidation(ME, NOW);

    const access = await evaluateOfflineAccess(NOW);
    expect(access.me).toEqual(ME);
    expect(access.lastValidatedAt?.toISOString()).toBe(NOW.toISOString());
  });

  it("sin instantánea no hay acceso sin conexión", async () => {
    expect((await evaluateOfflineAccess(NOW)).status).toBe("none");
  });
});

describe("plazo sin conexión de 7 días", () => {
  it.each([
    ["6 días", 6 * DAY, "allowed"],
    ["exactamente 7 días", OFFLINE_GRACE_MS, "allowed"],
    ["7 días y 1 ms", OFFLINE_GRACE_MS + 1, "expired"],
  ])("tras %s → %s", async (_, elapsed, status) => {
    await saveValidation(ME, NOW);

    const access = await evaluateOfflineAccess(new Date(NOW.getTime() + elapsed));

    expect(access.status).toBe(status);
  });

  it("al vencer explica qué hacer en español", async () => {
    await saveValidation(ME, NOW);

    const access = await evaluateOfflineAccess(new Date(NOW.getTime() + 8 * DAY));

    expect(access.message).toMatch(/conéctate a internet/i);
  });
});

describe("revalidación al reconectar", () => {
  it("renueva primero y luego consulta /me con el token nuevo", async () => {
    api();

    const me = await revalidate(NOW);

    expect(calls).toEqual(["refresh", "me:Bearer nuevo"]);
    expect(me).toEqual(ME);
    expect((await evaluateOfflineAccess(NOW)).lastValidatedAt?.toISOString()).toBe(
      NOW.toISOString(),
    );
  });

  it("si la renovación falla no se actualiza la instantánea", async () => {
    api(401);
    await saveValidation(ME, new Date(NOW.getTime() - DAY));

    await expect(revalidate(NOW)).rejects.toBeInstanceOf(ApiProblem);

    expect(calls).toEqual(["refresh"]);
    expect((await evaluateOfflineAccess(NOW)).lastValidatedAt?.toISOString()).toBe(
      new Date(NOW.getTime() - DAY).toISOString(),
    );
  });

  it("el token de acceso nunca se guarda en IndexedDB", async () => {
    api();
    await revalidate(NOW);

    const stored = JSON.stringify(await db.meta.toArray());
    expect(stored).not.toContain("nuevo");
    expect(stored).not.toContain("access_token");
  });
});

describe("useCanSync", () => {
  it("solo permite sincronizar después de revalidar, y se apaga sin conexión", async () => {
    api();
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(true);
    const { result } = renderHook(() => useCanSync());

    expect(result.current).toBe(false);
    await waitFor(() => expect(result.current).toBe(true));
    expect(calls).toEqual(["refresh", "me:Bearer nuevo"]);

    setOnline(false);
    expect(result.current).toBe(false);

    calls = [];
    setOnline(true);
    expect(result.current).toBe(false);
    await waitFor(() => expect(result.current).toBe(true));
    expect(calls).toEqual(["refresh", "me:Bearer nuevo"]);
  });

  it("si la revalidación falla no permite sincronizar", async () => {
    api(401);
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(true);
    const { result } = renderHook(() => useCanSync());

    await waitFor(() => expect(calls).toEqual(["refresh"]));
    expect(result.current).toBe(false);
  });
});
