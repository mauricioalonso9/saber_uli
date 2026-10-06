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

import type { HealthStatus, ServiceUnavailableResponse } from "./model";

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

export const getGetHealthUrl = () => {
  return `/api/health`;
};

/**
 * @summary El proceso está vivo
 */
export const getHealth = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<HealthStatus> => {
  return customInstance<HealthStatus>(getGetHealthUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetHealthQueryKey = () => {
  return [`/api/health`] as const;
};

export const getGetHealthQueryOptions = <
  TData = Awaited<ReturnType<typeof getHealth>>,
  TError = unknown,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getHealth>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetHealthQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getHealth>>> = ({ signal }) =>
    getHealth({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getHealth>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetHealthQueryResult = NonNullable<Awaited<ReturnType<typeof getHealth>>>;
export type GetHealthQueryError = unknown;

export function useGetHealth<TData = Awaited<ReturnType<typeof getHealth>>, TError = unknown>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getHealth>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getHealth>>,
          TError,
          Awaited<ReturnType<typeof getHealth>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetHealth<TData = Awaited<ReturnType<typeof getHealth>>, TError = unknown>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getHealth>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getHealth>>,
          TError,
          Awaited<ReturnType<typeof getHealth>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetHealth<TData = Awaited<ReturnType<typeof getHealth>>, TError = unknown>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getHealth>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary El proceso está vivo
 */

export function useGetHealth<TData = Awaited<ReturnType<typeof getHealth>>, TError = unknown>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getHealth>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetHealthQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetReadinessUrl = () => {
  return `/api/ready`;
};

/**
 * @summary Base de datos y Redis disponibles
 */
export const getReadiness = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<HealthStatus> => {
  return customInstance<HealthStatus>(getGetReadinessUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetReadinessQueryKey = () => {
  return [`/api/ready`] as const;
};

export const getGetReadinessQueryOptions = <
  TData = Awaited<ReturnType<typeof getReadiness>>,
  TError = ServiceUnavailableResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getReadiness>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetReadinessQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getReadiness>>> = ({ signal }) =>
    getReadiness({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getReadiness>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetReadinessQueryResult = NonNullable<Awaited<ReturnType<typeof getReadiness>>>;
export type GetReadinessQueryError = ServiceUnavailableResponse;

export function useGetReadiness<
  TData = Awaited<ReturnType<typeof getReadiness>>,
  TError = ServiceUnavailableResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getReadiness>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getReadiness>>,
          TError,
          Awaited<ReturnType<typeof getReadiness>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetReadiness<
  TData = Awaited<ReturnType<typeof getReadiness>>,
  TError = ServiceUnavailableResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getReadiness>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getReadiness>>,
          TError,
          Awaited<ReturnType<typeof getReadiness>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetReadiness<
  TData = Awaited<ReturnType<typeof getReadiness>>,
  TError = ServiceUnavailableResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getReadiness>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Base de datos y Redis disponibles
 */

export function useGetReadiness<
  TData = Awaited<ReturnType<typeof getReadiness>>,
  TError = ServiceUnavailableResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getReadiness>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetReadinessQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
