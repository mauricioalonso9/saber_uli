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

import type { ConsentRequiredResponse, Program, UnauthorizedResponse } from "./model";

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

export const getListActiveProgramsUrl = () => {
  return `/api/v1/programs`;
};

/**
 * @summary Programas activos para completar el perfil
 */
export const listActivePrograms = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<Program[]> => {
  return customInstance<Program[]>(getListActiveProgramsUrl(), {
    ...options,
    method: "GET",
  });
};

export const getListActiveProgramsQueryKey = () => {
  return [`/api/v1/programs`] as const;
};

export const getListActiveProgramsQueryOptions = <
  TData = Awaited<ReturnType<typeof listActivePrograms>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listActivePrograms>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListActiveProgramsQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listActivePrograms>>> = ({ signal }) =>
    listActivePrograms({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listActivePrograms>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListActiveProgramsQueryResult = NonNullable<
  Awaited<ReturnType<typeof listActivePrograms>>
>;
export type ListActiveProgramsQueryError = UnauthorizedResponse | ConsentRequiredResponse;

export function useListActivePrograms<
  TData = Awaited<ReturnType<typeof listActivePrograms>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listActivePrograms>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listActivePrograms>>,
          TError,
          Awaited<ReturnType<typeof listActivePrograms>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListActivePrograms<
  TData = Awaited<ReturnType<typeof listActivePrograms>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listActivePrograms>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listActivePrograms>>,
          TError,
          Awaited<ReturnType<typeof listActivePrograms>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListActivePrograms<
  TData = Awaited<ReturnType<typeof listActivePrograms>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listActivePrograms>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Programas activos para completar el perfil
 */

export function useListActivePrograms<
  TData = Awaited<ReturnType<typeof listActivePrograms>>,
  TError = UnauthorizedResponse | ConsentRequiredResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listActivePrograms>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListActiveProgramsQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
