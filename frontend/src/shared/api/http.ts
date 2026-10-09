/**
 * Mutador de orval: todas las llamadas del cliente generado pasan por `customInstance`
 * (T063; research R-14 a R-17).
 *
 * - Agrega `Authorization: Bearer <token>` con el token en memoria y `X-Requested-With:
 *   saber-uli` (lo exigen refresh y logout; en el resto es inocuo).
 * - Ante un 401 renueva una sola vez con `POST /api/auth/refresh` y reintenta. Las peticiones
 *   concurrentes comparten la misma renovación. No renueva en las rutas `/api/auth/` ni ante
 *   `reauthentication-required`, que exige volver a autenticarse (R-15).
 * - Convierte cada error en un `ApiProblem` (RFC 9457) con el mensaje en español.
 *
 * Firma exigida por orval v8: `customInstance<T>(url, options)`; la URL ya trae los parámetros
 * de consulta y el cuerpo ya viene serializado en `options.body`.
 */
import type { SessionTokens } from "@/api/model";
import { useSessionStore } from "@/features/auth/session-store";
import {
  PROBLEM_PREFIX,
  problemMessage,
  problemSlug,
  slugForStatus,
} from "@/shared/api/problem-messages";

const REFRESH_URL = "/api/auth/refresh";
const AUTH_PREFIX = "/api/auth/";

export interface FieldError {
  field: string;
  message: string;
}

/** Error de la API con forma RFC 9457; `message` es el texto en español para mostrar. */
export class ApiProblem extends Error {
  readonly status: number;
  readonly type: string;
  /** Parte final del `type` (`account-disabled`, `validation-error`, …). */
  readonly slug: string;
  readonly title: string;
  readonly detail?: string;
  readonly errors?: FieldError[];

  constructor(init: {
    status: number;
    type: string;
    title?: string;
    detail?: string;
    errors?: FieldError[];
  }) {
    super(problemMessage(init.type, init.status));
    this.name = "ApiProblem";
    this.status = init.status;
    this.type = init.type;
    this.slug = problemSlug(init.type) ?? slugForStatus(init.status) ?? "unknown";
    this.title = init.title ?? this.message;
    this.detail = init.detail;
    this.errors = init.errors;
  }
}

function clientProblem(status: number): ApiProblem {
  const slug = slugForStatus(status);
  return new ApiProblem({ status, type: slug ? `${PROBLEM_PREFIX}${slug}` : "about:blank" });
}

async function toProblem(response: Response): Promise<ApiProblem> {
  const body: unknown = await response.json().catch(() => null);
  if (body && typeof body === "object" && typeof (body as { type?: unknown }).type === "string") {
    const p = body as { type: string; title?: string; detail?: string; errors?: FieldError[] };
    return new ApiProblem({ ...p, status: response.status });
  }
  return clientProblem(response.status);
}

async function send(url: string, options: RequestInit, token: string | null): Promise<Response> {
  const headers = new Headers(options.headers);
  headers.set("X-Requested-With", "saber-uli");
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  try {
    return await fetch(url, { credentials: "same-origin", ...options, headers });
  } catch (error) {
    // Una petición cancelada no es un fallo de red: se propaga tal cual a TanStack Query.
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw clientProblem(0);
  }
}

let refreshInFlight: Promise<string> | null = null;

type SessionEndedListener = (slug: string) => void;
const sessionEndedListeners = new Set<SessionEndedListener>();

/**
 * Avisa cuando la renovación responde 401: la sesión terminó (por ejemplo, se revocó el acceso
 * del invitado). La app decide si lleva a `/ingresar` explicando la causa. Devuelve la función
 * para dejar de escuchar.
 */
export function onSessionEnded(listener: SessionEndedListener): () => void {
  sessionEndedListeners.add(listener);
  return () => sessionEndedListeners.delete(listener);
}

/**
 * Renueva el token de acceso con la cookie `su_refresh` y lo guarda en memoria. Si falla, borra
 * la sesión y lanza el `ApiProblem` con la causa (`session-expired`, `account-disabled`, …).
 * Las llamadas simultáneas comparten la misma petición.
 */
export function refreshAccessToken(): Promise<string> {
  refreshInFlight ??= (async () => {
    try {
      const response = await send(REFRESH_URL, { method: "POST" }, null);
      if (!response.ok) {
        const problem = await toProblem(response);
        if (response.status === 401) {
          useSessionStore.getState().clear();
          for (const listener of sessionEndedListeners) listener(problem.slug);
        }
        throw problem;
      }
      const tokens = (await response.json()) as SessionTokens;
      useSessionStore.getState().setSession(tokens.access_token, tokens.expires_in);
      return tokens.access_token;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export async function customInstance<T>(url: string, options: RequestInit = {}): Promise<T> {
  let response = await send(url, options, useSessionStore.getState().accessToken);

  if (response.status === 401 && !url.startsWith(AUTH_PREFIX)) {
    const problem = await toProblem(response);
    if (problem.slug === "reauthentication-required") throw problem;
    const token = await refreshAccessToken();
    response = await send(url, options, token);
  }

  if (!response.ok) throw await toProblem(response);
  return parse<T>(response);
}
