/**
 * Mutador de orval (stub de T005).
 *
 * T063 (Opus) lo completa con: token de acceso solo en memoria, cabecera `Authorization`,
 * renovación única ante 401 con `X-Requested-With: saber-uli` y traducción de cada `type` de
 * problema a un mensaje en español. Este stub solo hace el `fetch` mínimo para que el cliente
 * generado compile y funcione contra la API en desarrollo.
 *
 * Firma exigida por orval v8: `customInstance<T>(url, options)`; la URL ya trae los parámetros de
 * consulta incorporados (los genera orval con `getXxxUrl(params)`) y el cuerpo ya viene
 * serializado en `options.body`.
 */

/** Error de la API con forma RFC 9457 (application/problem+json). */
export interface ApiProblem extends Error {
  status: number;
  type: string;
  title: string;
  detail?: string;
  instance?: string;
  errors?: Record<string, unknown>;
}

export async function customInstance<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, options);

  if (!response.ok) {
    const problem = (await response.json().catch(() => ({}))) as Partial<ApiProblem>;
    const error = new Error(problem.title ?? `HTTP ${response.status}`) as ApiProblem;
    error.status = response.status;
    error.type = problem.type ?? "urn:saber-uli:problem:unknown";
    error.title = problem.title ?? `HTTP ${response.status}`;
    error.detail = problem.detail;
    error.instance = problem.instance;
    error.errors = problem.errors;
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
