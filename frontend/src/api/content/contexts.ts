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
  Context,
  ContextContent,
  ContextCreate,
  ContextUpdateResult,
  EditConflictResponse,
  ForbiddenResponse,
  ListContexts200,
  ListContextsParams,
  Media,
  NotFoundResponse,
  PreconditionRequiredResponse,
  Problem,
  TooManyRequestsResponse,
  UnauthorizedResponse,
  UploadContentMediaBody,
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

export const getUploadContentMediaUrl = () => {
  return `/api/v1/content/media`;
};

/**
 * @summary Sube una imagen (PNG, JPEG o WebP, ≤ 1 MB); se re-codifica sin metadatos (R-11)
 */
export const uploadContentMedia = async (
  uploadContentMediaBody: UploadContentMediaBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<Media> => {
  const formData = new FormData();
  formData.append(`file`, uploadContentMediaBody.file);

  return customInstance<Media>(getUploadContentMediaUrl(), {
    ...options,
    method: "POST",
    body: formData,
  });
};

export const getUploadContentMediaMutationKey = () => ["uploadContentMedia"] as const;

export const getUploadContentMediaMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | TooManyRequestsResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof uploadContentMedia>>,
    TError,
    UploadContentMediaMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof uploadContentMedia>>,
  TError,
  UploadContentMediaMutationVariables,
  TContext
> => {
  const mutationKey = getUploadContentMediaMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof uploadContentMedia>>,
    UploadContentMediaMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return uploadContentMedia(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UploadContentMediaMutationResult = NonNullable<
  Awaited<ReturnType<typeof uploadContentMedia>>
>;
export type UploadContentMediaMutationBody = UploadContentMediaBody;
export type UploadContentMediaMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | TooManyRequestsResponse;
export type UploadContentMediaMutationVariables = { data: UploadContentMediaBody };

/**
 * @summary Sube una imagen (PNG, JPEG o WebP, ≤ 1 MB); se re-codifica sin metadatos (R-11)
 */
export const useUploadContentMedia = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | TooManyRequestsResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof uploadContentMedia>>,
      TError,
      UploadContentMediaMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof uploadContentMedia>>,
  TError,
  UploadContentMediaMutationVariables,
  TContext
> => {
  return useMutation(getUploadContentMediaMutationOptions(options), queryClient);
};
export const getGetContentMediaUrl = (mediaId: string) => {
  return `/api/v1/content/media/${mediaId}`;
};

/**
 * Con `content:author`, cualquier imagen. Sin ese permiso, solo las imágenes de contextos
 * usados por una versión Publicada o Retirada; las demás responden 404 (FR-046, R-11).
 * @summary Entrega una imagen (cacheable e inmutable)
 */
export const getContentMedia = async (
  mediaId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Blob> => {
  return customInstance<Blob>(getGetContentMediaUrl(mediaId), {
    ...options,
    method: "GET",
  });
};

export const getGetContentMediaQueryKey = (mediaId: string) => {
  return [`/api/v1/content/media/${mediaId}`] as const;
};

export const getGetContentMediaQueryOptions = <
  TData = Awaited<ReturnType<typeof getContentMedia>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  mediaId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContentMedia>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetContentMediaQueryKey(mediaId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getContentMedia>>> = ({ signal }) =>
    getContentMedia(mediaId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: mediaId !== null && mediaId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getContentMedia>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetContentMediaQueryResult = NonNullable<Awaited<ReturnType<typeof getContentMedia>>>;
export type GetContentMediaQueryError = UnauthorizedResponse | NotFoundResponse;

export function useGetContentMedia<
  TData = Awaited<ReturnType<typeof getContentMedia>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  mediaId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContentMedia>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getContentMedia>>,
          TError,
          Awaited<ReturnType<typeof getContentMedia>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetContentMedia<
  TData = Awaited<ReturnType<typeof getContentMedia>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  mediaId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContentMedia>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getContentMedia>>,
          TError,
          Awaited<ReturnType<typeof getContentMedia>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetContentMedia<
  TData = Awaited<ReturnType<typeof getContentMedia>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  mediaId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContentMedia>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Entrega una imagen (cacheable e inmutable)
 */

export function useGetContentMedia<
  TData = Awaited<ReturnType<typeof getContentMedia>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  mediaId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContentMedia>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetContentMediaQueryOptions(mediaId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getListContextsUrl = (params?: ListContextsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/contexts?${stringifiedParams}`
    : `/api/v1/content/contexts`;
};

export const listContexts = async (
  params?: ListContextsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<ListContexts200> => {
  return customInstance<ListContexts200>(getListContextsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getListContextsQueryKey = (params?: ListContextsParams) => {
  return [`/api/v1/content/contexts`, ...(params ? [params] : [])] as const;
};

export const getListContextsQueryOptions = <
  TData = Awaited<ReturnType<typeof listContexts>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContextsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContexts>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListContextsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listContexts>>> = ({ signal }) =>
    listContexts(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listContexts>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListContextsQueryResult = NonNullable<Awaited<ReturnType<typeof listContexts>>>;
export type ListContextsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useListContexts<
  TData = Awaited<ReturnType<typeof listContexts>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | ListContextsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContexts>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listContexts>>,
          TError,
          Awaited<ReturnType<typeof listContexts>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListContexts<
  TData = Awaited<ReturnType<typeof listContexts>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContextsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContexts>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listContexts>>,
          TError,
          Awaited<ReturnType<typeof listContexts>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListContexts<
  TData = Awaited<ReturnType<typeof listContexts>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContextsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContexts>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useListContexts<
  TData = Awaited<ReturnType<typeof listContexts>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListContextsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listContexts>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListContextsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getCreateContextUrl = () => {
  return `/api/v1/content/contexts`;
};

export const createContext = async (
  contextCreate: ContextCreate,
  options?: Parameters<typeof customInstance>[1],
): Promise<Context> => {
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
  return customInstance<Context>(getCreateContextUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(contextCreate),
  });
};

export const getCreateContextMutationKey = () => ["createContext"] as const;

export const getCreateContextMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createContext>>,
    TError,
    CreateContextMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createContext>>,
  TError,
  CreateContextMutationVariables,
  TContext
> => {
  const mutationKey = getCreateContextMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createContext>>,
    CreateContextMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createContext(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateContextMutationResult = NonNullable<Awaited<ReturnType<typeof createContext>>>;
export type CreateContextMutationBody = ContextCreate;
export type CreateContextMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse;
export type CreateContextMutationVariables = { data: ContextCreate };

export const useCreateContext = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createContext>>,
      TError,
      CreateContextMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createContext>>,
  TError,
  CreateContextMutationVariables,
  TContext
> => {
  return useMutation(getCreateContextMutationOptions(options), queryClient);
};
export const getGetContextUrl = (contextCode: string) => {
  return `/api/v1/content/contexts/${contextCode}`;
};

export const getContext = async (
  contextCode: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Context> => {
  return customInstance<Context>(getGetContextUrl(contextCode), {
    ...options,
    method: "GET",
  });
};

export const getGetContextQueryKey = (contextCode: string) => {
  return [`/api/v1/content/contexts/${contextCode}`] as const;
};

export const getGetContextQueryOptions = <
  TData = Awaited<ReturnType<typeof getContext>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  contextCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContext>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetContextQueryKey(contextCode);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getContext>>> = ({ signal }) =>
    getContext(contextCode, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: contextCode !== null && contextCode !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getContext>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetContextQueryResult = NonNullable<Awaited<ReturnType<typeof getContext>>>;
export type GetContextQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetContext<
  TData = Awaited<ReturnType<typeof getContext>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  contextCode: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContext>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getContext>>,
          TError,
          Awaited<ReturnType<typeof getContext>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetContext<
  TData = Awaited<ReturnType<typeof getContext>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  contextCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContext>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getContext>>,
          TError,
          Awaited<ReturnType<typeof getContext>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetContext<
  TData = Awaited<ReturnType<typeof getContext>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  contextCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContext>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useGetContext<
  TData = Awaited<ReturnType<typeof getContext>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  contextCode: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getContext>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetContextQueryOptions(contextCode, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getUpdateContextUrl = (contextCode: string) => {
  return `/api/v1/content/contexts/${contextCode}`;
};

/**
 * @summary Crea una versión nueva del contexto; los ítems publicados que lo usan reciben versión nueva En revisión (FR-020)
 */
export const updateContext = async (
  contextCode: string,
  contextContent: ContextContent,
  options?: Parameters<typeof customInstance>[1],
): Promise<ContextUpdateResult> => {
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
  return customInstance<ContextUpdateResult>(getUpdateContextUrl(contextCode), {
    ...options,
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(contextContent),
  });
};

export const getUpdateContextMutationKey = () => ["updateContext"] as const;

export const getUpdateContextMutationOptions = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof updateContext>>,
    TError,
    UpdateContextMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof updateContext>>,
  TError,
  UpdateContextMutationVariables,
  TContext
> => {
  const mutationKey = getUpdateContextMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof updateContext>>,
    UpdateContextMutationVariables
  > = (props) => {
    const { contextCode, data } = props ?? {};

    return updateContext(contextCode, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UpdateContextMutationResult = NonNullable<Awaited<ReturnType<typeof updateContext>>>;
export type UpdateContextMutationBody = ContextContent;
export type UpdateContextMutationError =
  | UnauthorizedResponse
  | ForbiddenResponse
  | NotFoundResponse
  | EditConflictResponse
  | ValidationErrorResponse
  | PreconditionRequiredResponse;
export type UpdateContextMutationVariables = { contextCode: string; data: ContextContent };

/**
 * @summary Crea una versión nueva del contexto; los ítems publicados que lo usan reciben versión nueva En revisión (FR-020)
 */
export const useUpdateContext = <
  TError =
    | UnauthorizedResponse
    | ForbiddenResponse
    | NotFoundResponse
    | EditConflictResponse
    | ValidationErrorResponse
    | PreconditionRequiredResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof updateContext>>,
      TError,
      UpdateContextMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof updateContext>>,
  TError,
  UpdateContextMutationVariables,
  TContext
> => {
  return useMutation(getUpdateContextMutationOptions(options), queryClient);
};
