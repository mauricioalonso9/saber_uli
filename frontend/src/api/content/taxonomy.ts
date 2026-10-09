/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
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
  ContentModule,
  ForbiddenResponse,
  ListContentModules200,
  ListContentModulesParams,
  ListRubrics200,
  NotFoundResponse,
  Problem,
  Rubric,
  RubricInput,
  TaxonomyNode,
  TaxonomyNodeCreate,
  TaxonomyNodeUpdate,
  UnauthorizedResponse,
  UpdateContentModuleBody,
  ValidationErrorResponse,
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

export const getListContentModulesUrl = (params?: ListContentModulesParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/modules?${stringifiedParams}`
    : `/api/v1/content/modules`;
};

/**
 * @summary Módulos con su taxonomía completa, para formularios, filtros y cobertura
 */
export const listContentModules = async (
  params?: ListContentModulesParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<ListContentModules200> => {
  return customInstance<ListContentModules200>(getListContentModulesUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getListContentModulesQueryKey = (params?: ListContentModulesParams) => {
  return [`/api/v1/content/modules`, ...(params ? [params] : [])] as const;
};

export const getListContentModulesQueryOptions = <
  TData = Awaited<ReturnType<typeof listContentModules>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContentModulesParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContentModules>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListContentModulesQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listContentModules>>> = ({ signal }) =>
    listContentModules(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listContentModules>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListContentModulesQueryResult = NonNullable<
  Awaited<ReturnType<typeof listContentModules>>
>;
export type ListContentModulesQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useListContentModules<
  TData = Awaited<ReturnType<typeof listContentModules>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | ListContentModulesParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContentModules>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listContentModules>>,
          TError,
          Awaited<ReturnType<typeof listContentModules>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListContentModules<
  TData = Awaited<ReturnType<typeof listContentModules>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContentModulesParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof listContentModules>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listContentModules>>,
          TError,
          Awaited<ReturnType<typeof listContentModules>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListContentModules<
  TData = Awaited<ReturnType<typeof listContentModules>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContentModulesParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContentModules>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Módulos con su taxonomía completa, para formularios, filtros y cobertura
 */

export function useListContentModules<
  TData = Awaited<ReturnType<typeof listContentModules>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContentModulesParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContentModules>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListContentModulesQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getUpdateContentModuleUrl = (moduleCode: "LC" | "RC" | "CC" | "ING" | "CE") => {
  return `/api/v1/content/modules/${moduleCode}`;
};

/**
 * @summary Cambia la meta de ítems del módulo para la cobertura (FR-040)
 */
export const updateContentModule = async (
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE",
  updateContentModuleBody: UpdateContentModuleBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<ContentModule> => {
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
  return customInstance<ContentModule>(getUpdateContentModuleUrl(moduleCode), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(updateContentModuleBody),
  });
};

export const getUpdateContentModuleMutationKey = () => ["updateContentModule"] as const;

export const getUpdateContentModuleMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof updateContentModule>>,
    TError,
    UpdateContentModuleMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof updateContentModule>>,
  TError,
  UpdateContentModuleMutationVariables,
  TContext
> => {
  const mutationKey = getUpdateContentModuleMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof updateContentModule>>,
    UpdateContentModuleMutationVariables
  > = (props) => {
    const { moduleCode, data } = props ?? {};

    return updateContentModule(moduleCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UpdateContentModuleMutationResult = NonNullable<
  Awaited<ReturnType<typeof updateContentModule>>
>;
export type UpdateContentModuleMutationBody = UpdateContentModuleBody;
export type UpdateContentModuleMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;
export type UpdateContentModuleMutationVariables = {
  moduleCode: "LC" | "RC" | "CC" | "ING" | "CE";
  data: UpdateContentModuleBody;
};

/**
 * @summary Cambia la meta de ítems del módulo para la cobertura (FR-040)
 */
export const useUpdateContentModule = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof updateContentModule>>,
      TError,
      UpdateContentModuleMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof updateContentModule>>,
  TError,
  UpdateContentModuleMutationVariables,
  TContext
> => {
  return useMutation(getUpdateContentModuleMutationOptions(options), queryClient);
};
export const getCreateTaxonomyNodeUrl = () => {
  return `/api/v1/content/taxonomy-nodes`;
};

/**
 * @summary Agrega una categoría de la taxonomía (US9)
 */
export const createTaxonomyNode = async (
  taxonomyNodeCreate: TaxonomyNodeCreate,
  options?: Parameters<typeof customInstance>[1],
): Promise<TaxonomyNode> => {
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
  return customInstance<TaxonomyNode>(getCreateTaxonomyNodeUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(taxonomyNodeCreate),
  });
};

export const getCreateTaxonomyNodeMutationKey = () => ["createTaxonomyNode"] as const;

export const getCreateTaxonomyNodeMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createTaxonomyNode>>,
    TError,
    CreateTaxonomyNodeMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createTaxonomyNode>>,
  TError,
  CreateTaxonomyNodeMutationVariables,
  TContext
> => {
  const mutationKey = getCreateTaxonomyNodeMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createTaxonomyNode>>,
    CreateTaxonomyNodeMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createTaxonomyNode(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateTaxonomyNodeMutationResult = NonNullable<
  Awaited<ReturnType<typeof createTaxonomyNode>>
>;
export type CreateTaxonomyNodeMutationBody = TaxonomyNodeCreate;
export type CreateTaxonomyNodeMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse;
export type CreateTaxonomyNodeMutationVariables = { data: TaxonomyNodeCreate };

/**
 * @summary Agrega una categoría de la taxonomía (US9)
 */
export const useCreateTaxonomyNode = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createTaxonomyNode>>,
      TError,
      CreateTaxonomyNodeMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createTaxonomyNode>>,
  TError,
  CreateTaxonomyNodeMutationVariables,
  TContext
> => {
  return useMutation(getCreateTaxonomyNodeMutationOptions(options), queryClient);
};
export const getUpdateTaxonomyNodeUrl = (nodeId: string) => {
  return `/api/v1/content/taxonomy-nodes/${nodeId}`;
};

/**
 * @summary Edita nombre, descripción, peso objetivo o estado activo (FR-045)
 */
export const updateTaxonomyNode = async (
  nodeId: string,
  taxonomyNodeUpdate: TaxonomyNodeUpdate,
  options?: Parameters<typeof customInstance>[1],
): Promise<TaxonomyNode> => {
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
  return customInstance<TaxonomyNode>(getUpdateTaxonomyNodeUrl(nodeId), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(taxonomyNodeUpdate),
  });
};

export const getUpdateTaxonomyNodeMutationKey = () => ["updateTaxonomyNode"] as const;

export const getUpdateTaxonomyNodeMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof updateTaxonomyNode>>,
    TError,
    UpdateTaxonomyNodeMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof updateTaxonomyNode>>,
  TError,
  UpdateTaxonomyNodeMutationVariables,
  TContext
> => {
  const mutationKey = getUpdateTaxonomyNodeMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof updateTaxonomyNode>>,
    UpdateTaxonomyNodeMutationVariables
  > = (props) => {
    const { nodeId, data } = props ?? {};

    return updateTaxonomyNode(nodeId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UpdateTaxonomyNodeMutationResult = NonNullable<
  Awaited<ReturnType<typeof updateTaxonomyNode>>
>;
export type UpdateTaxonomyNodeMutationBody = TaxonomyNodeUpdate;
export type UpdateTaxonomyNodeMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;
export type UpdateTaxonomyNodeMutationVariables = { nodeId: string; data: TaxonomyNodeUpdate };

/**
 * @summary Edita nombre, descripción, peso objetivo o estado activo (FR-045)
 */
export const useUpdateTaxonomyNode = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof updateTaxonomyNode>>,
      TError,
      UpdateTaxonomyNodeMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof updateTaxonomyNode>>,
  TError,
  UpdateTaxonomyNodeMutationVariables,
  TContext
> => {
  return useMutation(getUpdateTaxonomyNodeMutationOptions(options), queryClient);
};
export const getDeleteTaxonomyNodeUrl = (nodeId: string) => {
  return `/api/v1/content/taxonomy-nodes/${nodeId}`;
};

/**
 * @summary Borra una categoría sin uso; si está en uso, se debe desactivar (FR-045)
 */
export const deleteTaxonomyNode = async (
  nodeId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<void> => {
  return customInstance<void>(getDeleteTaxonomyNodeUrl(nodeId), {
    ...options,
    method: "DELETE",
  });
};

export const getDeleteTaxonomyNodeMutationKey = () => ["deleteTaxonomyNode"] as const;

export const getDeleteTaxonomyNodeMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof deleteTaxonomyNode>>,
    TError,
    DeleteTaxonomyNodeMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof deleteTaxonomyNode>>,
  TError,
  DeleteTaxonomyNodeMutationVariables,
  TContext
> => {
  const mutationKey = getDeleteTaxonomyNodeMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof deleteTaxonomyNode>>,
    DeleteTaxonomyNodeMutationVariables
  > = (props) => {
    const { nodeId } = props ?? {};

    return deleteTaxonomyNode(nodeId, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type DeleteTaxonomyNodeMutationResult = NonNullable<
  Awaited<ReturnType<typeof deleteTaxonomyNode>>
>;

export type DeleteTaxonomyNodeMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem;
export type DeleteTaxonomyNodeMutationVariables = { nodeId: string };

/**
 * @summary Borra una categoría sin uso; si está en uso, se debe desactivar (FR-045)
 */
export const useDeleteTaxonomyNode = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof deleteTaxonomyNode>>,
      TError,
      DeleteTaxonomyNodeMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof deleteTaxonomyNode>>,
  TError,
  DeleteTaxonomyNodeMutationVariables,
  TContext
> => {
  return useMutation(getDeleteTaxonomyNodeMutationOptions(options), queryClient);
};
export const getListRubricsUrl = () => {
  return `/api/v1/content/rubrics`;
};

export const listRubrics = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<ListRubrics200> => {
  return customInstance<ListRubrics200>(getListRubricsUrl(), {
    ...options,
    method: "GET",
  });
};

export const getListRubricsQueryKey = () => {
  return [`/api/v1/content/rubrics`] as const;
};

export const getListRubricsQueryOptions = <
  TData = Awaited<ReturnType<typeof listRubrics>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listRubrics>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListRubricsQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listRubrics>>> = ({ signal }) =>
    listRubrics({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listRubrics>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListRubricsQueryResult = NonNullable<Awaited<ReturnType<typeof listRubrics>>>;
export type ListRubricsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useListRubrics<
  TData = Awaited<ReturnType<typeof listRubrics>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listRubrics>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listRubrics>>,
          TError,
          Awaited<ReturnType<typeof listRubrics>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListRubrics<
  TData = Awaited<ReturnType<typeof listRubrics>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listRubrics>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listRubrics>>,
          TError,
          Awaited<ReturnType<typeof listRubrics>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListRubrics<
  TData = Awaited<ReturnType<typeof listRubrics>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listRubrics>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useListRubrics<
  TData = Awaited<ReturnType<typeof listRubrics>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listRubrics>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListRubricsQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getCreateRubricUrl = () => {
  return `/api/v1/content/rubrics`;
};

export const createRubric = async (
  rubricInput: RubricInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Rubric> => {
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
  return customInstance<Rubric>(getCreateRubricUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(rubricInput),
  });
};

export const getCreateRubricMutationKey = () => ["createRubric"] as const;

export const getCreateRubricMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createRubric>>,
    TError,
    CreateRubricMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createRubric>>,
  TError,
  CreateRubricMutationVariables,
  TContext
> => {
  const mutationKey = getCreateRubricMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createRubric>>,
    CreateRubricMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createRubric(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateRubricMutationResult = NonNullable<Awaited<ReturnType<typeof createRubric>>>;
export type CreateRubricMutationBody = RubricInput;
export type CreateRubricMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse;
export type CreateRubricMutationVariables = { data: RubricInput };

export const useCreateRubric = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createRubric>>,
      TError,
      CreateRubricMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createRubric>>,
  TError,
  CreateRubricMutationVariables,
  TContext
> => {
  return useMutation(getCreateRubricMutationOptions(options), queryClient);
};
export const getUpdateRubricUrl = (rubricId: string) => {
  return `/api/v1/content/rubrics/${rubricId}`;
};

export const updateRubric = async (
  rubricId: string,
  rubricInput: RubricInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Rubric> => {
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
  return customInstance<Rubric>(getUpdateRubricUrl(rubricId), {
    ...options,
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(rubricInput),
  });
};

export const getUpdateRubricMutationKey = () => ["updateRubric"] as const;

export const getUpdateRubricMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof updateRubric>>,
    TError,
    UpdateRubricMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof updateRubric>>,
  TError,
  UpdateRubricMutationVariables,
  TContext
> => {
  const mutationKey = getUpdateRubricMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof updateRubric>>,
    UpdateRubricMutationVariables
  > = (props) => {
    const { rubricId, data } = props ?? {};

    return updateRubric(rubricId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UpdateRubricMutationResult = NonNullable<Awaited<ReturnType<typeof updateRubric>>>;
export type UpdateRubricMutationBody = RubricInput;
export type UpdateRubricMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;
export type UpdateRubricMutationVariables = { rubricId: string; data: RubricInput };

export const useUpdateRubric = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof updateRubric>>,
      TError,
      UpdateRubricMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof updateRubric>>,
  TError,
  UpdateRubricMutationVariables,
  TContext
> => {
  return useMutation(getUpdateRubricMutationOptions(options), queryClient);
};
