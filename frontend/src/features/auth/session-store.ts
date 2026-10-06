import { create } from "zustand";

/**
 * Sesión en memoria (research R-14, R-17).
 *
 * El token de acceso vive solo aquí, en memoria: NO se usa `persist` ni se escribe en
 * localStorage, sessionStorage o IndexedDB. Al recargar la página se pierde y se recupera con
 * `POST /api/auth/refresh` (la cookie `su_refresh` es HttpOnly y el código no la ve).
 */
interface SessionState {
  accessToken: string | null;
  /** Vencimiento del token de acceso en milisegundos desde la época. */
  expiresAt: number | null;
  setSession: (accessToken: string, expiresInSeconds: number) => void;
  clear: () => void;
}

export const useSessionStore = create<SessionState>()((set) => ({
  accessToken: null,
  expiresAt: null,
  setSession: (accessToken, expiresInSeconds) =>
    set({ accessToken, expiresAt: Date.now() + expiresInSeconds * 1000 }),
  clear: () => set({ accessToken: null, expiresAt: null }),
}));
