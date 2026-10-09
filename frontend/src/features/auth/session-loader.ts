/**
 * Estado de la sesión para las guardias (T067). Se calcula una vez y se reutiliza; el arranque
 * tras el ingreso y el cierre de sesión (T080) llaman a `invalidate()`.
 *
 * - Con conexión: renovación + `/me` (`revalidate`).
 * - Sin conexión: la instantánea de Dexie si tiene 7 días o menos; si no, `offline-expired`.
 * - Cualquier otro fallo (sesión vencida o revocada): anónimo.
 */
import type { SessionState } from "@/app/guards";
import { evaluateOfflineAccess, revalidate } from "@/features/auth/offline-access";
import { ApiProblem } from "@/shared/api/http";

export async function loadSession(): Promise<SessionState> {
  try {
    return { kind: "authenticated", me: await revalidate() };
  } catch (error) {
    if (error instanceof ApiProblem && error.slug === "network-error") {
      const offline = await evaluateOfflineAccess();
      if (offline.status === "allowed" && offline.me) {
        return { kind: "authenticated", me: offline.me };
      }
      if (offline.status === "expired") {
        return { kind: "offline-expired" };
      }
    }
    return { kind: "anonymous" };
  }
}

export interface SessionLoader {
  (): Promise<SessionState>;
  invalidate: () => void;
}

export function createSessionLoader(
  load: () => Promise<SessionState> = loadSession,
): SessionLoader {
  let cached: Promise<SessionState> | null = null;
  const get = (() => {
    cached ??= load().catch((): SessionState => ({ kind: "anonymous" }));
    return cached;
  }) as SessionLoader;
  get.invalidate = () => {
    cached = null;
  };
  return get;
}
