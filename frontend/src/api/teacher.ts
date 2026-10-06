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

import type {
  ForbiddenResponse,
  GroupStudentPage,
  GroupSummary,
  ListMyGroupStudentsParams,
  NotFoundResponse,
  UnauthorizedResponse,
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

export const getListMyTeachingGroupsUrl = () => {
  return `/api/v1/teacher/groups`;
};

/**
 * @summary Grupos donde el usuario es docente (FR-027)
 */
export const listMyTeachingGroups = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<GroupSummary[]> => {
  return customInstance<GroupSummary[]>(getListMyTeachingGroupsUrl(), {
    ...options,
    method: "GET",
  });
};

export const getListMyTeachingGroupsQueryKey = () => {
  return [`/api/v1/teacher/groups`] as const;
};

export const getListMyTeachingGroupsQueryOptions = <
  TData = Awaited<ReturnType<typeof listMyTeachingGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listMyTeachingGroups>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListMyTeachingGroupsQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listMyTeachingGroups>>> = ({ signal }) =>
    listMyTeachingGroups({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listMyTeachingGroups>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListMyTeachingGroupsQueryResult = NonNullable<
  Awaited<ReturnType<typeof listMyTeachingGroups>>
>;
export type ListMyTeachingGroupsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useListMyTeachingGroups<
  TData = Awaited<ReturnType<typeof listMyTeachingGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyTeachingGroups>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listMyTeachingGroups>>,
          TError,
          Awaited<ReturnType<typeof listMyTeachingGroups>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListMyTeachingGroups<
  TData = Awaited<ReturnType<typeof listMyTeachingGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyTeachingGroups>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listMyTeachingGroups>>,
          TError,
          Awaited<ReturnType<typeof listMyTeachingGroups>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListMyTeachingGroups<
  TData = Awaited<ReturnType<typeof listMyTeachingGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyTeachingGroups>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Grupos donde el usuario es docente (FR-027)
 */

export function useListMyTeachingGroups<
  TData = Awaited<ReturnType<typeof listMyTeachingGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyTeachingGroups>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListMyTeachingGroupsQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getListMyGroupStudentsUrl = (groupId: string, params?: ListMyGroupStudentsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/teacher/groups/${groupId}/students?${stringifiedParams}`
    : `/api/v1/teacher/groups/${groupId}/students`;
};

/**
 * @summary Estudiantes de un grupo propio (nombre, sin correo) (FR-027)
 */
export const listMyGroupStudents = async (
  groupId: string,
  params?: ListMyGroupStudentsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<GroupStudentPage> => {
  return customInstance<GroupStudentPage>(getListMyGroupStudentsUrl(groupId, params), {
    ...options,
    method: "GET",
  });
};

export const getListMyGroupStudentsQueryKey = (
  groupId: string,
  params?: ListMyGroupStudentsParams,
) => {
  return [`/api/v1/teacher/groups/${groupId}/students`, ...(params ? [params] : [])] as const;
};

export const getListMyGroupStudentsQueryOptions = <
  TData = Awaited<ReturnType<typeof listMyGroupStudents>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: ListMyGroupStudentsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyGroupStudents>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListMyGroupStudentsQueryKey(groupId, params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listMyGroupStudents>>> = ({ signal }) =>
    listMyGroupStudents(groupId, params, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: groupId !== null && groupId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof listMyGroupStudents>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type ListMyGroupStudentsQueryResult = NonNullable<
  Awaited<ReturnType<typeof listMyGroupStudents>>
>;
export type ListMyGroupStudentsQueryError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useListMyGroupStudents<
  TData = Awaited<ReturnType<typeof listMyGroupStudents>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params: undefined | ListMyGroupStudentsParams,
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyGroupStudents>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listMyGroupStudents>>,
          TError,
          Awaited<ReturnType<typeof listMyGroupStudents>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListMyGroupStudents<
  TData = Awaited<ReturnType<typeof listMyGroupStudents>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: ListMyGroupStudentsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyGroupStudents>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listMyGroupStudents>>,
          TError,
          Awaited<ReturnType<typeof listMyGroupStudents>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListMyGroupStudents<
  TData = Awaited<ReturnType<typeof listMyGroupStudents>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: ListMyGroupStudentsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyGroupStudents>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Estudiantes de un grupo propio (nombre, sin correo) (FR-027)
 */

export function useListMyGroupStudents<
  TData = Awaited<ReturnType<typeof listMyGroupStudents>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: ListMyGroupStudentsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listMyGroupStudents>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListMyGroupStudentsQueryOptions(groupId, params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
