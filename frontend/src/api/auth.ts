/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import type {
  DataTag,
  DefinedInitialDataOptions,
  DefinedUseQueryResult,
  MutationFunction,
  QueryClient,
  QueryFunction,
  QueryKey,
  UndefinedInitialDataOptions,
  UseMutationOptions,
  UseMutationResult,
  UseQueryOptions,
  UseQueryResult,
} from "@tanstack/react-query";

import type {
  Accepted,
  CompleteMicrosoftLoginParams,
  CreateGuestSessionBody,
  Problem,
  RequestGuestSignInLinkBody,
  SessionTokens,
  StartMicrosoftLoginParams,
  TooManyRequestsResponse,
  ValidationErrorResponse,
} from "./model";

import { customInstance } from "../shared/api/http";

type SecondParameter<T extends (...args: never) => unknown> = Parameters<T>[1];

const withQueryKey = <T extends object, K>(query: T, queryKey: K): T & { queryKey: K } => {
  const result = { queryKey } as T & { queryKey: K };
  for (const key of Object.keys(query)) {
    // The explicit queryKey always wins, matching the previous
    // `{ ...query, queryKey }` spread where it was set last.
    if (key === "queryKey") continue;
    Object.defineProperty(result, key, {
      enumerable: true,
      configurable: true,
      get: () => (query as Record<string, unknown>)[key],
    });
  }
  return result;
};

export const getStartMicrosoftLoginUrl = (params?: StartMicrosoftLoginParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/auth/microsoft/login?${stringifiedParams}`
    : `/api/auth/microsoft/login`;
};

/**
 * Redirige a Microsoft Entra ID con authorization code + PKCE.
 * @summary Inicia el ingreso con la cuenta institucional (FR-001)
 */
export const startMicrosoftLogin = async (
  params?: StartMicrosoftLoginParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<unknown> => {
  return customInstance<unknown>(getStartMicrosoftLoginUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getStartMicrosoftLoginQueryKey = (params?: StartMicrosoftLoginParams) => {
  return [`/api/auth/microsoft/login`, ...(params ? [params] : [])] as const;
};

export const getStartMicrosoftLoginQueryOptions = <
  TData = Awaited<ReturnType<typeof startMicrosoftLogin>>,
  TError = void | TooManyRequestsResponse,
>(
  params?: StartMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof startMicrosoftLogin>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getStartMicrosoftLoginQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof startMicrosoftLogin>>> = ({ signal }) =>
    startMicrosoftLogin(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof startMicrosoftLogin>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type StartMicrosoftLoginQueryResult = NonNullable<
  Awaited<ReturnType<typeof startMicrosoftLogin>>
>;
export type StartMicrosoftLoginQueryError = void | TooManyRequestsResponse;

export function useStartMicrosoftLogin<
  TData = Awaited<ReturnType<typeof startMicrosoftLogin>>,
  TError = void | TooManyRequestsResponse,
>(
  params: undefined | StartMicrosoftLoginParams,
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof startMicrosoftLogin>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof startMicrosoftLogin>>,
          TError,
          Awaited<ReturnType<typeof startMicrosoftLogin>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useStartMicrosoftLogin<
  TData = Awaited<ReturnType<typeof startMicrosoftLogin>>,
  TError = void | TooManyRequestsResponse,
>(
  params?: StartMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof startMicrosoftLogin>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof startMicrosoftLogin>>,
          TError,
          Awaited<ReturnType<typeof startMicrosoftLogin>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useStartMicrosoftLogin<
  TData = Awaited<ReturnType<typeof startMicrosoftLogin>>,
  TError = void | TooManyRequestsResponse,
>(
  params?: StartMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof startMicrosoftLogin>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Inicia el ingreso con la cuenta institucional (FR-001)
 */

export function useStartMicrosoftLogin<
  TData = Awaited<ReturnType<typeof startMicrosoftLogin>>,
  TError = void | TooManyRequestsResponse,
>(
  params?: StartMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof startMicrosoftLogin>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getStartMicrosoftLoginQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getCompleteMicrosoftLoginUrl = (params: CompleteMicrosoftLoginParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/auth/microsoft/callback?${stringifiedParams}`
    : `/api/auth/microsoft/callback`;
};

/**
 * Valida state, nonce, firma del ID token, `iss` y `tid`. Si el inquilino no es el de
 * Unilibre, redirige a `/ingresar?error=tenant_not_allowed` sin crear cuenta. Si es
 * válido, crea o actualiza la cuenta, abre sesión, fija la cookie de renovación y redirige
 * al frontend (`/bienvenida/datos`, `/bienvenida/perfil` o `return_to`).
 * @summary Retorno desde Microsoft Entra ID (FR-002, FR-003, FR-005)
 */
export const completeMicrosoftLogin = async (
  params: CompleteMicrosoftLoginParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<unknown> => {
  return customInstance<unknown>(getCompleteMicrosoftLoginUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getCompleteMicrosoftLoginQueryKey = (params?: CompleteMicrosoftLoginParams) => {
  return [`/api/auth/microsoft/callback`, ...(params ? [params] : [])] as const;
};

export const getCompleteMicrosoftLoginQueryOptions = <
  TData = Awaited<ReturnType<typeof completeMicrosoftLogin>>,
  TError = void,
>(
  params: CompleteMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof completeMicrosoftLogin>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getCompleteMicrosoftLoginQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof completeMicrosoftLogin>>> = ({ signal }) =>
    completeMicrosoftLogin(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof completeMicrosoftLogin>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type CompleteMicrosoftLoginQueryResult = NonNullable<
  Awaited<ReturnType<typeof completeMicrosoftLogin>>
>;
export type CompleteMicrosoftLoginQueryError = void;

export function useCompleteMicrosoftLogin<
  TData = Awaited<ReturnType<typeof completeMicrosoftLogin>>,
  TError = void,
>(
  params: CompleteMicrosoftLoginParams,
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof completeMicrosoftLogin>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof completeMicrosoftLogin>>,
          TError,
          Awaited<ReturnType<typeof completeMicrosoftLogin>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useCompleteMicrosoftLogin<
  TData = Awaited<ReturnType<typeof completeMicrosoftLogin>>,
  TError = void,
>(
  params: CompleteMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof completeMicrosoftLogin>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof completeMicrosoftLogin>>,
          TError,
          Awaited<ReturnType<typeof completeMicrosoftLogin>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useCompleteMicrosoftLogin<
  TData = Awaited<ReturnType<typeof completeMicrosoftLogin>>,
  TError = void,
>(
  params: CompleteMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof completeMicrosoftLogin>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Retorno desde Microsoft Entra ID (FR-002, FR-003, FR-005)
 */

export function useCompleteMicrosoftLogin<
  TData = Awaited<ReturnType<typeof completeMicrosoftLogin>>,
  TError = void,
>(
  params: CompleteMicrosoftLoginParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof completeMicrosoftLogin>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getCompleteMicrosoftLoginQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getRequestGuestSignInLinkUrl = () => {
  return `/api/auth/guest/link-requests`;
};

/**
 * Responde siempre 202 con el mismo cuerpo, exista o no el correo.
 * @summary Un invitado pide un enlace de ingreso (FR-013)
 */
export const requestGuestSignInLink = async (
  requestGuestSignInLinkBody: RequestGuestSignInLinkBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<Accepted> => {
  const getHeaders = (
    h?: NonNullable<RequestInit["headers"]>,
  ): Record<string, string | readonly string[]> => {
    if (!h) return {};
    if (h instanceof Headers) return Object.fromEntries(h.entries());
    if (Symbol.iterator in h) {
      return Object.fromEntries(
        Array.from(
          h as Iterable<Iterable<string>>,
          (entry) => Array.from(entry) as [string, string],
        ),
      );
    }
    const headers: Record<string, string | readonly string[]> = {};
    for (const [name, value] of Object.entries<string | readonly string[] | undefined>(h)) {
      if (value !== undefined) headers[name] = value;
    }
    return headers;
  };
  return customInstance<Accepted>(getRequestGuestSignInLinkUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(requestGuestSignInLinkBody),
  });
};

export const getRequestGuestSignInLinkMutationKey = () => ["requestGuestSignInLink"] as const;

export const getRequestGuestSignInLinkMutationOptions = <
  TError = ValidationErrorResponse | TooManyRequestsResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof requestGuestSignInLink>>,
    TError,
    RequestGuestSignInLinkMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof requestGuestSignInLink>>,
  TError,
  RequestGuestSignInLinkMutationVariables,
  TContext
> => {
  const mutationKey = getRequestGuestSignInLinkMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof requestGuestSignInLink>>,
    RequestGuestSignInLinkMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return requestGuestSignInLink(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RequestGuestSignInLinkMutationResult = NonNullable<
  Awaited<ReturnType<typeof requestGuestSignInLink>>
>;
export type RequestGuestSignInLinkMutationBody = RequestGuestSignInLinkBody;
export type RequestGuestSignInLinkMutationError = ValidationErrorResponse | TooManyRequestsResponse;
export type RequestGuestSignInLinkMutationVariables = { data: RequestGuestSignInLinkBody };

/**
 * @summary Un invitado pide un enlace de ingreso (FR-013)
 */
export const useRequestGuestSignInLink = <
  TError = ValidationErrorResponse | TooManyRequestsResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof requestGuestSignInLink>>,
      TError,
      RequestGuestSignInLinkMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof requestGuestSignInLink>>,
  TError,
  RequestGuestSignInLinkMutationVariables,
  TContext
> => {
  return useMutation(getRequestGuestSignInLinkMutationOptions(options), queryClient);
};
export const getCreateGuestSessionUrl = () => {
  return `/api/auth/guest/sessions`;
};

/**
 * @summary Consume un enlace de invitación o de ingreso (FR-007, FR-011)
 */
export const createGuestSession = async (
  createGuestSessionBody: CreateGuestSessionBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<SessionTokens> => {
  const getHeaders = (
    h?: NonNullable<RequestInit["headers"]>,
  ): Record<string, string | readonly string[]> => {
    if (!h) return {};
    if (h instanceof Headers) return Object.fromEntries(h.entries());
    if (Symbol.iterator in h) {
      return Object.fromEntries(
        Array.from(
          h as Iterable<Iterable<string>>,
          (entry) => Array.from(entry) as [string, string],
        ),
      );
    }
    const headers: Record<string, string | readonly string[]> = {};
    for (const [name, value] of Object.entries<string | readonly string[] | undefined>(h)) {
      if (value !== undefined) headers[name] = value;
    }
    return headers;
  };
  return customInstance<SessionTokens>(getCreateGuestSessionUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(createGuestSessionBody),
  });
};

export const getCreateGuestSessionMutationKey = () => ["createGuestSession"] as const;

export const getCreateGuestSessionMutationOptions = <
  TError = Problem | TooManyRequestsResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createGuestSession>>,
    TError,
    CreateGuestSessionMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createGuestSession>>,
  TError,
  CreateGuestSessionMutationVariables,
  TContext
> => {
  const mutationKey = getCreateGuestSessionMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createGuestSession>>,
    CreateGuestSessionMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createGuestSession(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateGuestSessionMutationResult = NonNullable<
  Awaited<ReturnType<typeof createGuestSession>>
>;
export type CreateGuestSessionMutationBody = CreateGuestSessionBody;
export type CreateGuestSessionMutationError = Problem | TooManyRequestsResponse;
export type CreateGuestSessionMutationVariables = { data: CreateGuestSessionBody };

/**
 * @summary Consume un enlace de invitación o de ingreso (FR-007, FR-011)
 */
export const useCreateGuestSession = <
  TError = Problem | TooManyRequestsResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createGuestSession>>,
      TError,
      CreateGuestSessionMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createGuestSession>>,
  TError,
  CreateGuestSessionMutationVariables,
  TContext
> => {
  return useMutation(getCreateGuestSessionMutationOptions(options), queryClient);
};
export const getRefreshSessionUrl = () => {
  return `/api/auth/refresh`;
};

/**
 * Requiere la cookie `su_refresh` y la cabecera `X-Requested-With: saber-uli`. Valida que
 * la cuenta siga activa, que el acceso de invitado no haya vencido ni sido revocado y que
 * la sesión no haya superado 7 días de inactividad ni 30 días absolutos.
 * @summary Renueva el token de acceso y rota la cookie (FR-037, FR-038, FR-039)
 */
export const refreshSession = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<SessionTokens> => {
  return customInstance<SessionTokens>(getRefreshSessionUrl(), {
    ...options,
    method: "POST",
  });
};

export const getRefreshSessionMutationKey = () => ["refreshSession"] as const;

export const getRefreshSessionMutationOptions = <
  TError = Problem | TooManyRequestsResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<Awaited<ReturnType<typeof refreshSession>>, TError, void, TContext>;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<Awaited<ReturnType<typeof refreshSession>>, TError, void, TContext> => {
  const mutationKey = getRefreshSessionMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<Awaited<ReturnType<typeof refreshSession>>, void> = () => {
    return refreshSession(requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RefreshSessionMutationResult = NonNullable<Awaited<ReturnType<typeof refreshSession>>>;

export type RefreshSessionMutationError = Problem | TooManyRequestsResponse;

/**
 * @summary Renueva el token de acceso y rota la cookie (FR-037, FR-038, FR-039)
 */
export const useRefreshSession = <TError = Problem | TooManyRequestsResponse, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof refreshSession>>,
      TError,
      void,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<Awaited<ReturnType<typeof refreshSession>>, TError, void, TContext> => {
  return useMutation(getRefreshSessionMutationOptions(options), queryClient);
};
export const getLogoutUrl = () => {
  return `/api/auth/logout`;
};

/**
 * @summary Cierra la sesión actual (escenario 1.4)
 */
export const logout = async (options?: Parameters<typeof customInstance>[1]): Promise<void> => {
  return customInstance<void>(getLogoutUrl(), {
    ...options,
    method: "POST",
  });
};

export const getLogoutMutationKey = () => ["logout"] as const;

export const getLogoutMutationOptions = <TError = Problem, TContext = unknown>(options?: {
  mutation?: UseMutationOptions<Awaited<ReturnType<typeof logout>>, TError, void, TContext>;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<Awaited<ReturnType<typeof logout>>, TError, void, TContext> => {
  const mutationKey = getLogoutMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<Awaited<ReturnType<typeof logout>>, void> = () => {
    return logout(requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type LogoutMutationResult = NonNullable<Awaited<ReturnType<typeof logout>>>;

export type LogoutMutationError = Problem;

/**
 * @summary Cierra la sesión actual (escenario 1.4)
 */
export const useLogout = <TError = Problem, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<Awaited<ReturnType<typeof logout>>, TError, void, TContext>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<Awaited<ReturnType<typeof logout>>, TError, void, TContext> => {
  return useMutation(getLogoutMutationOptions(options), queryClient);
};
