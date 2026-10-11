/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
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

import type {
  ForbiddenResponse,
  GetItemStatistics200,
  ModuleCoverage,
  NotFoundResponse,
  UnauthorizedResponse,
} from "./model";

import { customInstance } from "../../shared/api/http";

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

export const getGetItemStatisticsUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/statistics`;
};

/**
 * @summary Estadísticas por versión publicada o retirada (FR-041 a FR-044)
 */
export const getItemStatistics = async (
  itemCode: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<GetItemStatistics200> => {
  return customInstance<GetItemStatistics200>(getGetItemStatisticsUrl(itemCode), {
    ...options,
    method: "GET",
  });
};

export const getGetItemStatisticsQueryKey = (itemCode: string) => {
  return [`/api/v1/content/items/${itemCode}/statistics`] as const;
};

export const getGetItemStatisticsQueryOptions = <
  TData = Awaited<ReturnType<typeof getItemStatistics>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemStatistics>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetItemStatisticsQueryKey(itemCode);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getItemStatistics>>> = ({ signal }) =>
    getItemStatistics(itemCode, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: itemCode !== null && itemCode !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getItemStatistics>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetItemStatisticsQueryResult = NonNullable<
  Awaited<ReturnType<typeof getItemStatistics>>
>;
export type GetItemStatisticsQueryError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetItemStatistics<
  TData = Awaited<ReturnType<typeof getItemStatistics>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemStatistics>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItemStatistics>>,
          TError,
          Awaited<ReturnType<typeof getItemStatistics>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItemStatistics<
  TData = Awaited<ReturnType<typeof getItemStatistics>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemStatistics>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItemStatistics>>,
          TError,
          Awaited<ReturnType<typeof getItemStatistics>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItemStatistics<
  TData = Awaited<ReturnType<typeof getItemStatistics>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemStatistics>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Estadísticas por versión publicada o retirada (FR-041 a FR-044)
 */

export function useGetItemStatistics<
  TData = Awaited<ReturnType<typeof getItemStatistics>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemStatistics>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetItemStatisticsQueryOptions(itemCode, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetModuleCoverageUrl = (moduleCode: "LC" | "RC" | "CC" | "ING" | "CE") => {
  return `/api/v1/content/coverage/${moduleCode}`;
};

/**
 * @summary Cobertura del módulo frente a la distribución objetivo (FR-039, SC-009)
 */
export const getModuleCoverage = async (
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  options?: Parameters<typeof customInstance>[1],
): Promise<ModuleCoverage> => {
  return customInstance<ModuleCoverage>(getGetModuleCoverageUrl(moduleCode), {
    ...options,
    method: "GET",
  });
};

export const getGetModuleCoverageQueryKey = (moduleCode: "LC" | "RC" | "CC" | "ING" | "CE") => {
  return [`/api/v1/content/coverage/${moduleCode}`] as const;
};

export const getGetModuleCoverageQueryOptions = <
  TData = Awaited<ReturnType<typeof getModuleCoverage>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getModuleCoverage>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetModuleCoverageQueryKey(moduleCode);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getModuleCoverage>>> = ({ signal }) =>
    getModuleCoverage(moduleCode, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: moduleCode !== null && moduleCode !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getModuleCoverage>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetModuleCoverageQueryResult = NonNullable<
  Awaited<ReturnType<typeof getModuleCoverage>>
>;
export type GetModuleCoverageQueryError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetModuleCoverage<
  TData = Awaited<ReturnType<typeof getModuleCoverage>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getModuleCoverage>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getModuleCoverage>>,
          TError,
          Awaited<ReturnType<typeof getModuleCoverage>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetModuleCoverage<
  TData = Awaited<ReturnType<typeof getModuleCoverage>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getModuleCoverage>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getModuleCoverage>>,
          TError,
          Awaited<ReturnType<typeof getModuleCoverage>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetModuleCoverage<
  TData = Awaited<ReturnType<typeof getModuleCoverage>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getModuleCoverage>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Cobertura del módulo frente a la distribución objetivo (FR-039, SC-009)
 */

export function useGetModuleCoverage<
  TData = Awaited<ReturnType<typeof getModuleCoverage>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getModuleCoverage>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetModuleCoverageQueryOptions(moduleCode, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
