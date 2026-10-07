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
  Consent,
  ConsentRequiredResponse,
  DecideConsentBody,
  DeletionRequest,
  ListMyConsents200,
  Me,
  NotFoundResponse,
  PersonalDataExport,
  Problem,
  Profile,
  ProfileUpdate,
  RequestMyDeletionBody,
  UnauthorizedResponse,
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

export const getGetMeUrl = () => {
  return `/api/v1/me`;
};

/**
 * @summary Estado de la cuenta, roles, permisos y pasos pendientes del primer ingreso
 */
export const getMe = async (options?: Parameters<typeof customInstance>[1]): Promise<Me> => {
  return customInstance<Me>(getGetMeUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetMeQueryKey = () => {
  return [`/api/v1/me`] as const;
};

export const getGetMeQueryOptions = <
  TData = Awaited<ReturnType<typeof getMe>>,
  TError = UnauthorizedResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMe>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetMeQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getMe>>> = ({ signal }) =>
    getMe({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getMe>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetMeQueryResult = NonNullable<Awaited<ReturnType<typeof getMe>>>;
export type GetMeQueryError = UnauthorizedResponse;

export function useGetMe<TData = Awaited<ReturnType<typeof getMe>>, TError = UnauthorizedResponse>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMe>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getMe>>,
          TError,
          Awaited<ReturnType<typeof getMe>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetMe<TData = Awaited<ReturnType<typeof getMe>>, TError = UnauthorizedResponse>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMe>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getMe>>,
          TError,
          Awaited<ReturnType<typeof getMe>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetMe<TData = Awaited<ReturnType<typeof getMe>>, TError = UnauthorizedResponse>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMe>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Estado de la cuenta, roles, permisos y pasos pendientes del primer ingreso
 */

export function useGetMe<TData = Awaited<ReturnType<typeof getMe>>, TError = UnauthorizedResponse>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMe>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetMeQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetMyProfileUrl = () => {
  return `/api/v1/me/profile`;
};

export const getMyProfile = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<Profile> => {
  return customInstance<Profile>(getGetMyProfileUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetMyProfileQueryKey = () => {
  return [`/api/v1/me/profile`] as const;
};

export const getGetMyProfileQueryOptions = <
  TData = Awaited<ReturnType<typeof getMyProfile>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMyProfile>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetMyProfileQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getMyProfile>>> = ({ signal }) =>
    getMyProfile({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getMyProfile>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetMyProfileQueryResult = NonNullable<Awaited<ReturnType<typeof getMyProfile>>>;
export type GetMyProfileQueryError = UnauthorizedResponse | ConsentRequiredResponse;

export function useGetMyProfile<
  TData = Awaited<ReturnType<typeof getMyProfile>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMyProfile>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getMyProfile>>,
          TError,
          Awaited<ReturnType<typeof getMyProfile>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetMyProfile<
  TData = Awaited<ReturnType<typeof getMyProfile>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMyProfile>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getMyProfile>>,
          TError,
          Awaited<ReturnType<typeof getMyProfile>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetMyProfile<
  TData = Awaited<ReturnType<typeof getMyProfile>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMyProfile>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useGetMyProfile<
  TData = Awaited<ReturnType<typeof getMyProfile>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMyProfile>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetMyProfileQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getUpdateMyProfileUrl = () => {
  return `/api/v1/me/profile`;
};

/**
 * @summary Completa o edita el perfil (FR-019, FR-020, FR-021)
 */
export const updateMyProfile = async (
  profileUpdate: ProfileUpdate,
  options?: Parameters<typeof customInstance>[1],
): Promise<Profile> => {
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
  return customInstance<Profile>(getUpdateMyProfileUrl(), {
    ...options,
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(profileUpdate),
  });
};

export const getUpdateMyProfileMutationKey = () => ["updateMyProfile"] as const;

export const getUpdateMyProfileMutationOptions = <
  TError = UnauthorizedResponse | ConsentRequiredResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof updateMyProfile>>,
    TError,
    UpdateMyProfileMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof updateMyProfile>>,
  TError,
  UpdateMyProfileMutationVariables,
  TContext
> => {
  const mutationKey = getUpdateMyProfileMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof updateMyProfile>>,
    UpdateMyProfileMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return updateMyProfile(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UpdateMyProfileMutationResult = NonNullable<
  Awaited<ReturnType<typeof updateMyProfile>>
>;
export type UpdateMyProfileMutationBody = ProfileUpdate;
export type UpdateMyProfileMutationError =
  UnauthorizedResponse | ConsentRequiredResponse | ValidationErrorResponse;
export type UpdateMyProfileMutationVariables = { data: ProfileUpdate };

/**
 * @summary Completa o edita el perfil (FR-019, FR-020, FR-021)
 */
export const useUpdateMyProfile = <
  TError = UnauthorizedResponse | ConsentRequiredResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof updateMyProfile>>,
      TError,
      UpdateMyProfileMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof updateMyProfile>>,
  TError,
  UpdateMyProfileMutationVariables,
  TContext
> => {
  return useMutation(getUpdateMyProfileMutationOptions(options), queryClient);
};
export const getListMyConsentsUrl = () => {
  return `/api/v1/me/consents`;
};

/**
 * @summary Historial de autorizaciones (escenario 2.4, FR-018)
 */
export const listMyConsents = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<ListMyConsents200> => {
  return customInstance<ListMyConsents200>(getListMyConsentsUrl(), {
    ...options,
    method: "GET",
  });
};

export const getListMyConsentsQueryKey = () => {
  return [`/api/v1/me/consents`] as const;
};

export const getListMyConsentsQueryOptions = <
  TData = Awaited<ReturnType<typeof listMyConsents>>,
  TError = UnauthorizedResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listMyConsents>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListMyConsentsQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listMyConsents>>> = ({ signal }) =>
    listMyConsents({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listMyConsents>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListMyConsentsQueryResult = NonNullable<Awaited<ReturnType<typeof listMyConsents>>>;
export type ListMyConsentsQueryError = UnauthorizedResponse;

export function useListMyConsents<
  TData = Awaited<ReturnType<typeof listMyConsents>>,
  TError = UnauthorizedResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listMyConsents>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listMyConsents>>,
          TError,
          Awaited<ReturnType<typeof listMyConsents>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListMyConsents<
  TData = Awaited<ReturnType<typeof listMyConsents>>,
  TError = UnauthorizedResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listMyConsents>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listMyConsents>>,
          TError,
          Awaited<ReturnType<typeof listMyConsents>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListMyConsents<
  TData = Awaited<ReturnType<typeof listMyConsents>>,
  TError = UnauthorizedResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listMyConsents>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Historial de autorizaciones (escenario 2.4, FR-018)
 */

export function useListMyConsents<
  TData = Awaited<ReturnType<typeof listMyConsents>>,
  TError = UnauthorizedResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listMyConsents>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListMyConsentsQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getDecideConsentUrl = () => {
  return `/api/v1/me/consents`;
};

/**
 * @summary Acepta o rechaza la versión vigente de la política (FR-015)
 */
export const decideConsent = async (
  decideConsentBody: DecideConsentBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<Consent> => {
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
  return customInstance<Consent>(getDecideConsentUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(decideConsentBody),
  });
};

export const getDecideConsentMutationKey = () => ["decideConsent"] as const;

export const getDecideConsentMutationOptions = <
  TError = UnauthorizedResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof decideConsent>>,
    TError,
    DecideConsentMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof decideConsent>>,
  TError,
  DecideConsentMutationVariables,
  TContext
> => {
  const mutationKey = getDecideConsentMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof decideConsent>>,
    DecideConsentMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return decideConsent(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type DecideConsentMutationResult = NonNullable<Awaited<ReturnType<typeof decideConsent>>>;
export type DecideConsentMutationBody = DecideConsentBody;
export type DecideConsentMutationError = UnauthorizedResponse | Problem | ValidationErrorResponse;
export type DecideConsentMutationVariables = { data: DecideConsentBody };

/**
 * @summary Acepta o rechaza la versión vigente de la política (FR-015)
 */
export const useDecideConsent = <
  TError = UnauthorizedResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof decideConsent>>,
      TError,
      DecideConsentMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof decideConsent>>,
  TError,
  DecideConsentMutationVariables,
  TContext
> => {
  return useMutation(getDecideConsentMutationOptions(options), queryClient);
};
export const getRevokeConsentUrl = () => {
  return `/api/v1/me/consents/revocation`;
};

/**
 * @summary Revoca la autorización vigente; suspende el acceso (escenario 2.5)
 */
export const revokeConsent = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<Consent> => {
  return customInstance<Consent>(getRevokeConsentUrl(), {
    ...options,
    method: "POST",
  });
};

export const getRevokeConsentMutationKey = () => ["revokeConsent"] as const;

export const getRevokeConsentMutationOptions = <
  TError = UnauthorizedResponse | Problem,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<Awaited<ReturnType<typeof revokeConsent>>, TError, void, TContext>;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<Awaited<ReturnType<typeof revokeConsent>>, TError, void, TContext> => {
  const mutationKey = getRevokeConsentMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<Awaited<ReturnType<typeof revokeConsent>>, void> = () => {
    return revokeConsent(requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RevokeConsentMutationResult = NonNullable<Awaited<ReturnType<typeof revokeConsent>>>;

export type RevokeConsentMutationError = UnauthorizedResponse | Problem;

/**
 * @summary Revoca la autorización vigente; suspende el acceso (escenario 2.5)
 */
export const useRevokeConsent = <TError = UnauthorizedResponse | Problem, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof revokeConsent>>,
      TError,
      void,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<Awaited<ReturnType<typeof revokeConsent>>, TError, void, TContext> => {
  return useMutation(getRevokeConsentMutationOptions(options), queryClient);
};
export const getExportMyDataUrl = () => {
  return `/api/v1/me/data-export`;
};

/**
 * @summary Descarga todos los datos personales del usuario (FR-031)
 */
export const exportMyData = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<PersonalDataExport> => {
  return customInstance<PersonalDataExport>(getExportMyDataUrl(), {
    ...options,
    method: "GET",
  });
};

export const getExportMyDataQueryKey = () => {
  return [`/api/v1/me/data-export`] as const;
};

export const getExportMyDataQueryOptions = <
  TData = Awaited<ReturnType<typeof exportMyData>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportMyData>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getExportMyDataQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof exportMyData>>> = ({ signal }) =>
    exportMyData({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof exportMyData>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ExportMyDataQueryResult = NonNullable<Awaited<ReturnType<typeof exportMyData>>>;
export type ExportMyDataQueryError = UnauthorizedResponse | ConsentRequiredResponse;

export function useExportMyData<
  TData = Awaited<ReturnType<typeof exportMyData>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportMyData>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof exportMyData>>,
          TError,
          Awaited<ReturnType<typeof exportMyData>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useExportMyData<
  TData = Awaited<ReturnType<typeof exportMyData>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportMyData>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof exportMyData>>,
          TError,
          Awaited<ReturnType<typeof exportMyData>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useExportMyData<
  TData = Awaited<ReturnType<typeof exportMyData>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportMyData>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Descarga todos los datos personales del usuario (FR-031)
 */

export function useExportMyData<
  TData = Awaited<ReturnType<typeof exportMyData>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportMyData>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getExportMyDataQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetMyDeletionRequestUrl = () => {
  return `/api/v1/me/deletion-request`;
};

export const getMyDeletionRequest = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<DeletionRequest> => {
  return customInstance<DeletionRequest>(getGetMyDeletionRequestUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetMyDeletionRequestQueryKey = () => {
  return [`/api/v1/me/deletion-request`] as const;
};

export const getGetMyDeletionRequestQueryOptions = <
  TData = Awaited<ReturnType<typeof getMyDeletionRequest>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getMyDeletionRequest>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetMyDeletionRequestQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getMyDeletionRequest>>> = ({ signal }) =>
    getMyDeletionRequest({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getMyDeletionRequest>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetMyDeletionRequestQueryResult = NonNullable<
  Awaited<ReturnType<typeof getMyDeletionRequest>>
>;
export type GetMyDeletionRequestQueryError = UnauthorizedResponse | NotFoundResponse;

export function useGetMyDeletionRequest<
  TData = Awaited<ReturnType<typeof getMyDeletionRequest>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof getMyDeletionRequest>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getMyDeletionRequest>>,
          TError,
          Awaited<ReturnType<typeof getMyDeletionRequest>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetMyDeletionRequest<
  TData = Awaited<ReturnType<typeof getMyDeletionRequest>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof getMyDeletionRequest>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getMyDeletionRequest>>,
          TError,
          Awaited<ReturnType<typeof getMyDeletionRequest>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetMyDeletionRequest<
  TData = Awaited<ReturnType<typeof getMyDeletionRequest>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof getMyDeletionRequest>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useGetMyDeletionRequest<
  TData = Awaited<ReturnType<typeof getMyDeletionRequest>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof getMyDeletionRequest>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetMyDeletionRequestQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getRequestMyDeletionUrl = () => {
  return `/api/v1/me/deletion-request`;
};

/**
 * @summary Solicita la supresión de la cuenta y los datos (FR-032)
 */
export const requestMyDeletion = async (
  requestMyDeletionBody: RequestMyDeletionBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<DeletionRequest> => {
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
  return customInstance<DeletionRequest>(getRequestMyDeletionUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(requestMyDeletionBody),
  });
};

export const getRequestMyDeletionMutationKey = () => ["requestMyDeletion"] as const;

export const getRequestMyDeletionMutationOptions = <
  TError = UnauthorizedResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof requestMyDeletion>>,
    TError,
    RequestMyDeletionMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof requestMyDeletion>>,
  TError,
  RequestMyDeletionMutationVariables,
  TContext
> => {
  const mutationKey = getRequestMyDeletionMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof requestMyDeletion>>,
    RequestMyDeletionMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return requestMyDeletion(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RequestMyDeletionMutationResult = NonNullable<
  Awaited<ReturnType<typeof requestMyDeletion>>
>;
export type RequestMyDeletionMutationBody = RequestMyDeletionBody;
export type RequestMyDeletionMutationError =
  UnauthorizedResponse | Problem | ValidationErrorResponse;
export type RequestMyDeletionMutationVariables = { data: RequestMyDeletionBody };

/**
 * @summary Solicita la supresión de la cuenta y los datos (FR-032)
 */
export const useRequestMyDeletion = <
  TError = UnauthorizedResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof requestMyDeletion>>,
      TError,
      RequestMyDeletionMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof requestMyDeletion>>,
  TError,
  RequestMyDeletionMutationVariables,
  TContext
> => {
  return useMutation(getRequestMyDeletionMutationOptions(options), queryClient);
};
