/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import { useQuery } from "@tanstack/react-query";
import type {
  DataTag,
  DefinedInitialDataOptions,
  DefinedUseQueryResult,
  QueryClient,
  QueryFunction,
  QueryKey,
  UndefinedInitialDataOptions,
  UseQueryOptions,
  UseQueryResult,
} from "@tanstack/react-query";

import type { NotFoundResponse, PolicyVersion } from "./model";

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

export const getGetCurrentPolicyUrl = () => {
  return `/api/v1/privacy-policy/current`;
};

/**
 * @summary Versión vigente de la política (FR-016)
 */
export const getCurrentPolicy = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<PolicyVersion> => {
  return customInstance<PolicyVersion>(getGetCurrentPolicyUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetCurrentPolicyQueryKey = () => {
  return [`/api/v1/privacy-policy/current`] as const;
};

export const getGetCurrentPolicyQueryOptions = <
  TData = Awaited<ReturnType<typeof getCurrentPolicy>>,
  TError = unknown,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getCurrentPolicy>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetCurrentPolicyQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getCurrentPolicy>>> = ({ signal }) =>
    getCurrentPolicy({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getCurrentPolicy>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetCurrentPolicyQueryResult = NonNullable<Awaited<ReturnType<typeof getCurrentPolicy>>>;
export type GetCurrentPolicyQueryError = unknown;

export function useGetCurrentPolicy<
  TData = Awaited<ReturnType<typeof getCurrentPolicy>>,
  TError = unknown,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getCurrentPolicy>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getCurrentPolicy>>,
          TError,
          Awaited<ReturnType<typeof getCurrentPolicy>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetCurrentPolicy<
  TData = Awaited<ReturnType<typeof getCurrentPolicy>>,
  TError = unknown,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getCurrentPolicy>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getCurrentPolicy>>,
          TError,
          Awaited<ReturnType<typeof getCurrentPolicy>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetCurrentPolicy<
  TData = Awaited<ReturnType<typeof getCurrentPolicy>>,
  TError = unknown,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getCurrentPolicy>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Versión vigente de la política (FR-016)
 */

export function useGetCurrentPolicy<
  TData = Awaited<ReturnType<typeof getCurrentPolicy>>,
  TError = unknown,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getCurrentPolicy>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetCurrentPolicyQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetPolicyVersionUrl = (policyVersionId: string) => {
  return `/api/v1/privacy-policy/versions/${policyVersionId}`;
};

/**
 * @summary Texto de una versión concreta (escenario 2.4)
 */
export const getPolicyVersion = async (
  policyVersionId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<PolicyVersion> => {
  return customInstance<PolicyVersion>(getGetPolicyVersionUrl(policyVersionId), {
    ...options,
    method: "GET",
  });
};

export const getGetPolicyVersionQueryKey = (policyVersionId: string) => {
  return [`/api/v1/privacy-policy/versions/${policyVersionId}`] as const;
};

export const getGetPolicyVersionQueryOptions = <
  TData = Awaited<ReturnType<typeof getPolicyVersion>>,
  TError = NotFoundResponse,
>(
  policyVersionId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getPolicyVersion>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetPolicyVersionQueryKey(policyVersionId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getPolicyVersion>>> = ({ signal }) =>
    getPolicyVersion(policyVersionId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: policyVersionId !== null && policyVersionId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getPolicyVersion>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetPolicyVersionQueryResult = NonNullable<Awaited<ReturnType<typeof getPolicyVersion>>>;
export type GetPolicyVersionQueryError = NotFoundResponse;

export function useGetPolicyVersion<
  TData = Awaited<ReturnType<typeof getPolicyVersion>>,
  TError = NotFoundResponse,
>(
  policyVersionId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getPolicyVersion>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getPolicyVersion>>,
          TError,
          Awaited<ReturnType<typeof getPolicyVersion>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetPolicyVersion<
  TData = Awaited<ReturnType<typeof getPolicyVersion>>,
  TError = NotFoundResponse,
>(
  policyVersionId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getPolicyVersion>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getPolicyVersion>>,
          TError,
          Awaited<ReturnType<typeof getPolicyVersion>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetPolicyVersion<
  TData = Awaited<ReturnType<typeof getPolicyVersion>>,
  TError = NotFoundResponse,
>(
  policyVersionId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getPolicyVersion>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Texto de una versión concreta (escenario 2.4)
 */

export function useGetPolicyVersion<
  TData = Awaited<ReturnType<typeof getPolicyVersion>>,
  TError = NotFoundResponse,
>(
  policyVersionId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getPolicyVersion>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetPolicyVersionQueryOptions(policyVersionId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
