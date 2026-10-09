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
  ApproveItemBody,
  CommentInput,
  EditConflictResponse,
  ForbiddenResponse,
  GetItemVersion200,
  InvalidTransitionResponse,
  Item,
  ItemContent,
  ItemCreate,
  ItemEvent,
  ItemHistory,
  ListItems200,
  ListItemsParams,
  NotFoundResponse,
  PreconditionRequiredResponse,
  Problem,
  ReasonInput,
  SaveItemDraftParams,
  UnauthorizedResponse,
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

export const getListItemsUrl = (params?: ListItemsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/items?${stringifiedParams}`
    : `/api/v1/content/items`;
};

/**
 * @summary Busca y filtra el banco (SC-009)
 */
export const listItems = async (
  params?: ListItemsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<ListItems200> => {
  return customInstance<ListItems200>(getListItemsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getListItemsQueryKey = (params?: ListItemsParams) => {
  return [`/api/v1/content/items`, ...(params ? [params] : [])] as const;
};

export const getListItemsQueryOptions = <
  TData = Awaited<ReturnType<typeof listItems>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listItems>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListItemsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listItems>>> = ({ signal }) =>
    listItems(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listItems>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListItemsQueryResult = NonNullable<Awaited<ReturnType<typeof listItems>>>;
export type ListItemsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useListItems<
  TData = Awaited<ReturnType<typeof listItems>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | ListItemsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listItems>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listItems>>,
          TError,
          Awaited<ReturnType<typeof listItems>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListItems<
  TData = Awaited<ReturnType<typeof listItems>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listItems>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listItems>>,
          TError,
          Awaited<ReturnType<typeof listItems>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListItems<
  TData = Awaited<ReturnType<typeof listItems>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listItems>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Busca y filtra el banco (SC-009)
 */

export function useListItems<
  TData = Awaited<ReturnType<typeof listItems>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listItems>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListItemsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getCreateItemUrl = () => {
  return `/api/v1/content/items`;
};

/**
 * @summary Crea un ítem o consigna en Borrador (FR-024)
 */
export const createItem = async (
  itemCreate: ItemCreate,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
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
  return customInstance<Item>(getCreateItemUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(itemCreate),
  });
};

export const getCreateItemMutationKey = () => ["createItem"] as const;

export const getCreateItemMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createItem>>,
    TError,
    CreateItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createItem>>,
  TError,
  CreateItemMutationVariables,
  TContext
> => {
  const mutationKey = getCreateItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createItem>>,
    CreateItemMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createItem(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateItemMutationResult = NonNullable<Awaited<ReturnType<typeof createItem>>>;
export type CreateItemMutationBody = ItemCreate;
export type CreateItemMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse;
export type CreateItemMutationVariables = { data: ItemCreate };

/**
 * @summary Crea un ítem o consigna en Borrador (FR-024)
 */
export const useCreateItem = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createItem>>,
      TError,
      CreateItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createItem>>,
  TError,
  CreateItemMutationVariables,
  TContext
> => {
  return useMutation(getCreateItemMutationOptions(options), queryClient);
};
export const getGetItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}`;
};

/**
 * @summary Ítem con su versión publicada y su versión abierta
 */
export const getItem = async (
  itemCode: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
  return customInstance<Item>(getGetItemUrl(itemCode), {
    ...options,
    method: "GET",
  });
};

export const getGetItemQueryKey = (itemCode: string) => {
  return [`/api/v1/content/items/${itemCode}`] as const;
};

export const getGetItemQueryOptions = <
  TData = Awaited<ReturnType<typeof getItem>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItem>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetItemQueryKey(itemCode);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getItem>>> = ({ signal }) =>
    getItem(itemCode, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: itemCode !== null && itemCode !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getItem>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetItemQueryResult = NonNullable<Awaited<ReturnType<typeof getItem>>>;
export type GetItemQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetItem<
  TData = Awaited<ReturnType<typeof getItem>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItem>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItem>>,
          TError,
          Awaited<ReturnType<typeof getItem>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItem<
  TData = Awaited<ReturnType<typeof getItem>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItem>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItem>>,
          TError,
          Awaited<ReturnType<typeof getItem>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItem<
  TData = Awaited<ReturnType<typeof getItem>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItem>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Ítem con su versión publicada y su versión abierta
 */

export function useGetItem<
  TData = Awaited<ReturnType<typeof getItem>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItem>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetItemQueryOptions(itemCode, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getSaveItemDraftUrl = (itemCode: string, params?: SaveItemDraftParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/items/${itemCode}/draft?${stringifiedParams}`
    : `/api/v1/content/items/${itemCode}/draft`;
};

/**
 * @summary Guarda la versión abierta; si no hay, crea una a partir de la vigente (FR-015, FR-016)
 */
export const saveItemDraft = async (
  itemCode: string,
  itemContent: ItemContent,
  params?: SaveItemDraftParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
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
  return customInstance<Item>(getSaveItemDraftUrl(itemCode, params), {
    ...options,
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(itemContent),
  });
};

export const getSaveItemDraftMutationKey = () => ["saveItemDraft"] as const;

export const getSaveItemDraftMutationOptions = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | Problem
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof saveItemDraft>>,
    TError,
    SaveItemDraftMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof saveItemDraft>>,
  TError,
  SaveItemDraftMutationVariables,
  TContext
> => {
  const mutationKey = getSaveItemDraftMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof saveItemDraft>>,
    SaveItemDraftMutationVariables
  > = (props) => {
    const { itemCode, data, params } = props ?? {};

    return saveItemDraft(itemCode, data, params, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type SaveItemDraftMutationResult = NonNullable<Awaited<ReturnType<typeof saveItemDraft>>>;
export type SaveItemDraftMutationBody = ItemContent;
export type SaveItemDraftMutationError =
  | UnauthorizedResponse
  | ForbiddenResponse
  | NotFoundResponse
  | Problem
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type SaveItemDraftMutationVariables = {
  itemCode: string;
  data: ItemContent;
  params?: SaveItemDraftParams;
};

/**
 * @summary Guarda la versión abierta; si no hay, crea una a partir de la vigente (FR-015, FR-016)
 */
export const useSaveItemDraft = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | Problem
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof saveItemDraft>>,
      TError,
      SaveItemDraftMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof saveItemDraft>>,
  TError,
  SaveItemDraftMutationVariables,
  TContext
> => {
  return useMutation(getSaveItemDraftMutationOptions(options), queryClient);
};
export const getSubmitItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/submission`;
};

/**
 * @summary Envía la versión en Borrador a revisión; exige contenido completo y válido
 */
export const submitItem = async (
  itemCode: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
  return customInstance<Item>(getSubmitItemUrl(itemCode), {
    ...options,
    method: "POST",
  });
};

export const getSubmitItemMutationKey = () => ["submitItem"] as const;

export const getSubmitItemMutationOptions = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof submitItem>>,
    TError,
    SubmitItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof submitItem>>,
  TError,
  SubmitItemMutationVariables,
  TContext
> => {
  const mutationKey = getSubmitItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof submitItem>>,
    SubmitItemMutationVariables
  > = (props) => {
    const { itemCode } = props ?? {};

    return submitItem(itemCode, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type SubmitItemMutationResult = NonNullable<Awaited<ReturnType<typeof submitItem>>>;

export type SubmitItemMutationError =
  | UnauthorizedResponse
  | ForbiddenResponse
  | NotFoundResponse
  | InvalidTransitionResponse
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type SubmitItemMutationVariables = { itemCode: string };

/**
 * @summary Envía la versión en Borrador a revisión; exige contenido completo y válido
 */
export const useSubmitItem = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof submitItem>>,
      TError,
      SubmitItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof submitItem>>,
  TError,
  SubmitItemMutationVariables,
  TContext
> => {
  return useMutation(getSubmitItemMutationOptions(options), queryClient);
};
export const getApproveItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/approval`;
};

/**
 * @summary Publica la versión En revisión (FR-012 a FR-015)
 */
export const approveItem = async (
  itemCode: string,
  approveItemBody: ApproveItemBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
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
  return customInstance<Item>(getApproveItemUrl(itemCode), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(approveItemBody),
  });
};

export const getApproveItemMutationKey = () => ["approveItem"] as const;

export const getApproveItemMutationOptions = <
  TError =
    | UnauthorizedResponse
    | Problem
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof approveItem>>,
    TError,
    ApproveItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof approveItem>>,
  TError,
  ApproveItemMutationVariables,
  TContext
> => {
  const mutationKey = getApproveItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof approveItem>>,
    ApproveItemMutationVariables
  > = (props) => {
    const { itemCode, data } = props ?? {};

    return approveItem(itemCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type ApproveItemMutationResult = NonNullable<Awaited<ReturnType<typeof approveItem>>>;
export type ApproveItemMutationBody = ApproveItemBody;
export type ApproveItemMutationError =
  | UnauthorizedResponse
  | Problem
  | NotFoundResponse
  | InvalidTransitionResponse
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type ApproveItemMutationVariables = { itemCode: string; data: ApproveItemBody };

/**
 * @summary Publica la versión En revisión (FR-012 a FR-015)
 */
export const useApproveItem = <
  TError =
    | UnauthorizedResponse
    | Problem
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof approveItem>>,
      TError,
      ApproveItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof approveItem>>,
  TError,
  ApproveItemMutationVariables,
  TContext
> => {
  return useMutation(getApproveItemMutationOptions(options), queryClient);
};
export const getReturnItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/return`;
};

/**
 * @summary Devuelve la versión En revisión a Borrador con comentarios
 */
export const returnItem = async (
  itemCode: string,
  commentInput: CommentInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
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
  return customInstance<Item>(getReturnItemUrl(itemCode), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(commentInput),
  });
};

export const getReturnItemMutationKey = () => ["returnItem"] as const;

export const getReturnItemMutationOptions = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof returnItem>>,
    TError,
    ReturnItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof returnItem>>,
  TError,
  ReturnItemMutationVariables,
  TContext
> => {
  const mutationKey = getReturnItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof returnItem>>,
    ReturnItemMutationVariables
  > = (props) => {
    const { itemCode, data } = props ?? {};

    return returnItem(itemCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type ReturnItemMutationResult = NonNullable<Awaited<ReturnType<typeof returnItem>>>;
export type ReturnItemMutationBody = CommentInput;
export type ReturnItemMutationError =
  | UnauthorizedResponse
  | ForbiddenResponse
  | NotFoundResponse
  | InvalidTransitionResponse
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type ReturnItemMutationVariables = { itemCode: string; data: CommentInput };

/**
 * @summary Devuelve la versión En revisión a Borrador con comentarios
 */
export const useReturnItem = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof returnItem>>,
      TError,
      ReturnItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof returnItem>>,
  TError,
  ReturnItemMutationVariables,
  TContext
> => {
  return useMutation(getReturnItemMutationOptions(options), queryClient);
};
export const getRejectItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/rejection`;
};

/**
 * @summary Rechaza la versión En revisión; pasa a Retirada con el motivo
 */
export const rejectItem = async (
  itemCode: string,
  reasonInput: ReasonInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
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
  return customInstance<Item>(getRejectItemUrl(itemCode), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(reasonInput),
  });
};

export const getRejectItemMutationKey = () => ["rejectItem"] as const;

export const getRejectItemMutationOptions = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof rejectItem>>,
    TError,
    RejectItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof rejectItem>>,
  TError,
  RejectItemMutationVariables,
  TContext
> => {
  const mutationKey = getRejectItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof rejectItem>>,
    RejectItemMutationVariables
  > = (props) => {
    const { itemCode, data } = props ?? {};

    return rejectItem(itemCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RejectItemMutationResult = NonNullable<Awaited<ReturnType<typeof rejectItem>>>;
export type RejectItemMutationBody = ReasonInput;
export type RejectItemMutationError =
  | UnauthorizedResponse
  | ForbiddenResponse
  | NotFoundResponse
  | InvalidTransitionResponse
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type RejectItemMutationVariables = { itemCode: string; data: ReasonInput };

/**
 * @summary Rechaza la versión En revisión; pasa a Retirada con el motivo
 */
export const useRejectItem = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof rejectItem>>,
      TError,
      RejectItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof rejectItem>>,
  TError,
  RejectItemMutationVariables,
  TContext
> => {
  return useMutation(getRejectItemMutationOptions(options), queryClient);
};
export const getRetireItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/retirement`;
};

/**
 * @summary Retira la versión publicada; deja de entregarse en la práctica nueva
 */
export const retireItem = async (
  itemCode: string,
  reasonInput: ReasonInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Item> => {
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
  return customInstance<Item>(getRetireItemUrl(itemCode), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(reasonInput),
  });
};

export const getRetireItemMutationKey = () => ["retireItem"] as const;

export const getRetireItemMutationOptions = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof retireItem>>,
    TError,
    RetireItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof retireItem>>,
  TError,
  RetireItemMutationVariables,
  TContext
> => {
  const mutationKey = getRetireItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof retireItem>>,
    RetireItemMutationVariables
  > = (props) => {
    const { itemCode, data } = props ?? {};

    return retireItem(itemCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RetireItemMutationResult = NonNullable<Awaited<ReturnType<typeof retireItem>>>;
export type RetireItemMutationBody = ReasonInput;
export type RetireItemMutationError =
  | UnauthorizedResponse
  | ForbiddenResponse
  | NotFoundResponse
  | InvalidTransitionResponse
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type RetireItemMutationVariables = { itemCode: string; data: ReasonInput };

/**
 * @summary Retira la versión publicada; deja de entregarse en la práctica nueva
 */
export const useRetireItem = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | InvalidTransitionResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof retireItem>>,
      TError,
      RetireItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof retireItem>>,
  TError,
  RetireItemMutationVariables,
  TContext
> => {
  return useMutation(getRetireItemMutationOptions(options), queryClient);
};
export const getCommentItemUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/comments`;
};

/**
 * @summary Comenta el ítem (docentes y administradores); queda en la historia
 */
export const commentItem = async (
  itemCode: string,
  commentInput: CommentInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<ItemEvent> => {
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
  return customInstance<ItemEvent>(getCommentItemUrl(itemCode), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(commentInput),
  });
};

export const getCommentItemMutationKey = () => ["commentItem"] as const;

export const getCommentItemMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof commentItem>>,
    TError,
    CommentItemMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof commentItem>>,
  TError,
  CommentItemMutationVariables,
  TContext
> => {
  const mutationKey = getCommentItemMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof commentItem>>,
    CommentItemMutationVariables
  > = (props) => {
    const { itemCode, data } = props ?? {};

    return commentItem(itemCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CommentItemMutationResult = NonNullable<Awaited<ReturnType<typeof commentItem>>>;
export type CommentItemMutationBody = CommentInput;
export type CommentItemMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;
export type CommentItemMutationVariables = { itemCode: string; data: CommentInput };

/**
 * @summary Comenta el ítem (docentes y administradores); queda en la historia
 */
export const useCommentItem = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof commentItem>>,
      TError,
      CommentItemMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof commentItem>>,
  TError,
  CommentItemMutationVariables,
  TContext
> => {
  return useMutation(getCommentItemMutationOptions(options), queryClient);
};
export const getGetItemHistoryUrl = (itemCode: string) => {
  return `/api/v1/content/items/${itemCode}/history`;
};

/**
 * @summary Versiones y eventos del ítem (FR-018)
 */
export const getItemHistory = async (
  itemCode: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<ItemHistory> => {
  return customInstance<ItemHistory>(getGetItemHistoryUrl(itemCode), {
    ...options,
    method: "GET",
  });
};

export const getGetItemHistoryQueryKey = (itemCode: string) => {
  return [`/api/v1/content/items/${itemCode}/history`] as const;
};

export const getGetItemHistoryQueryOptions = <
  TData = Awaited<ReturnType<typeof getItemHistory>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemHistory>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetItemHistoryQueryKey(itemCode);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getItemHistory>>> = ({ signal }) =>
    getItemHistory(itemCode, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: itemCode !== null && itemCode !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getItemHistory>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetItemHistoryQueryResult = NonNullable<Awaited<ReturnType<typeof getItemHistory>>>;
export type GetItemHistoryQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetItemHistory<
  TData = Awaited<ReturnType<typeof getItemHistory>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemHistory>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItemHistory>>,
          TError,
          Awaited<ReturnType<typeof getItemHistory>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItemHistory<
  TData = Awaited<ReturnType<typeof getItemHistory>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemHistory>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItemHistory>>,
          TError,
          Awaited<ReturnType<typeof getItemHistory>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItemHistory<
  TData = Awaited<ReturnType<typeof getItemHistory>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemHistory>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Versiones y eventos del ítem (FR-018)
 */

export function useGetItemHistory<
  TData = Awaited<ReturnType<typeof getItemHistory>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemHistory>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetItemHistoryQueryOptions(itemCode, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetItemVersionUrl = (itemCode: string, versionNumber: number) => {
  return `/api/v1/content/items/${itemCode}/versions/${versionNumber}`;
};

/**
 * @summary Contenido completo de una versión y sus diferencias con la anterior
 */
export const getItemVersion = async (
  itemCode: string,
  versionNumber: number,
  options?: Parameters<typeof customInstance>[1],
): Promise<GetItemVersion200> => {
  return customInstance<GetItemVersion200>(getGetItemVersionUrl(itemCode, versionNumber), {
    ...options,
    method: "GET",
  });
};

export const getGetItemVersionQueryKey = (itemCode: string, versionNumber: number) => {
  return [`/api/v1/content/items/${itemCode}/versions/${versionNumber}`] as const;
};

export const getGetItemVersionQueryOptions = <
  TData = Awaited<ReturnType<typeof getItemVersion>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  versionNumber: number,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemVersion>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetItemVersionQueryKey(itemCode, versionNumber);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getItemVersion>>> = ({ signal }) =>
    getItemVersion(itemCode, versionNumber, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled:
      itemCode !== null &&
      itemCode !== undefined &&
      versionNumber !== null &&
      versionNumber !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getItemVersion>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetItemVersionQueryResult = NonNullable<Awaited<ReturnType<typeof getItemVersion>>>;
export type GetItemVersionQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetItemVersion<
  TData = Awaited<ReturnType<typeof getItemVersion>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  versionNumber: number,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemVersion>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItemVersion>>,
          TError,
          Awaited<ReturnType<typeof getItemVersion>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItemVersion<
  TData = Awaited<ReturnType<typeof getItemVersion>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  versionNumber: number,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemVersion>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getItemVersion>>,
          TError,
          Awaited<ReturnType<typeof getItemVersion>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetItemVersion<
  TData = Awaited<ReturnType<typeof getItemVersion>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  versionNumber: number,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemVersion>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Contenido completo de una versión y sus diferencias con la anterior
 */

export function useGetItemVersion<
  TData = Awaited<ReturnType<typeof getItemVersion>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  itemCode: string,
  versionNumber: number,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getItemVersion>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetItemVersionQueryOptions(itemCode, versionNumber, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
