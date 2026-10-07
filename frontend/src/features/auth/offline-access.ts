/**
 * Acceso sin conexión (FR-038, FR-039; research R-17).
 *
 * - Tras cada validación con el servidor se guarda en Dexie la instantánea de `/api/v1/me` y la
 *   fecha (`lastValidatedAt`).
 * - Sin conexión, la app sigue usable si `ahora − lastValidatedAt ≤ 7 días`; después se bloquea
 *   con un mensaje.
 * - Al reconectar se renueva primero la sesión (`/api/auth/refresh`) y luego se consulta
 *   `/api/v1/me`; solo entonces `useCanSync()` permite sincronizar (la spec 003 lo usa antes de
 *   enviar progreso guardado sin conexión).
 */
import { useEffect, useState } from "react";

import { getMe } from "@/api/me";
import type { Me } from "@/api/model";
import { refreshAccessToken } from "@/shared/api/http";
import { db } from "@/shared/db/dexie";

export const OFFLINE_GRACE_MS = 7 * 24 * 60 * 60 * 1000;
const SNAPSHOT_KEY = "me-snapshot";

export const OFFLINE_EXPIRED_MESSAGE =
  "Pasaron más de 7 días sin validar tu acceso. Conéctate a internet para seguir usando Saber Uli.";

interface Snapshot {
  me: Me;
  lastValidatedAt: string;
}

export type OfflineAccessStatus = "allowed" | "expired" | "none";

export interface OfflineAccess {
  status: OfflineAccessStatus;
  me?: Me;
  lastValidatedAt?: Date;
  message?: string;
}

export async function saveValidation(me: Me, now: Date = new Date()): Promise<void> {
  const snapshot: Snapshot = { me, lastValidatedAt: now.toISOString() };
  await db.meta.put({ key: SNAPSHOT_KEY, value: snapshot });
}

/** Al cerrar sesión: sin instantánea, la app ya no se puede usar sin conexión. */
export async function clearOfflineSnapshot(): Promise<void> {
  await db.meta.delete(SNAPSHOT_KEY);
}

export async function evaluateOfflineAccess(now: Date = new Date()): Promise<OfflineAccess> {
  const entry = await db.meta.get(SNAPSHOT_KEY);
  const snapshot = entry?.value as Snapshot | undefined;
  if (!snapshot) {
    return { status: "none" };
  }
  const lastValidatedAt = new Date(snapshot.lastValidatedAt);
  const elapsed = now.getTime() - lastValidatedAt.getTime();
  if (elapsed > OFFLINE_GRACE_MS) {
    return {
      status: "expired",
      me: snapshot.me,
      lastValidatedAt,
      message: OFFLINE_EXPIRED_MESSAGE,
    };
  }
  return { status: "allowed", me: snapshot.me, lastValidatedAt };
}

/** Renueva la sesión y luego consulta `/me`; guarda la instantánea solo si ambas funcionan. */
export async function revalidate(now: Date = new Date()): Promise<Me> {
  await refreshAccessToken();
  const me = await getMe();
  await saveValidation(me, now);
  return me;
}

/**
 * `true` solo cuando hay conexión y la sesión se revalidó desde la última reconexión. Se vuelve
 * `false` al perder la conexión y mientras dura la revalidación.
 */
export function useCanSync(): boolean {
  const [canSync, setCanSync] = useState(false);

  useEffect(() => {
    let active = true;
    let attempt = 0;

    const check = () => {
      setCanSync(false);
      if (!navigator.onLine) {
        return;
      }
      const current = ++attempt;
      revalidate()
        .then(() => {
          if (active && current === attempt && navigator.onLine) {
            setCanSync(true);
          }
        })
        .catch(() => {
          // Sin sesión válida no se sincroniza; las guardias (T067) llevan al ingreso.
        });
    };
    const goOffline = () => {
      attempt += 1;
      setCanSync(false);
    };

    check();
    window.addEventListener("online", check);
    window.addEventListener("offline", goOffline);
    return () => {
      active = false;
      window.removeEventListener("online", check);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return canSync;
}
