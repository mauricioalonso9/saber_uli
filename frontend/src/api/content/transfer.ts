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
  ConfirmImportBody,
  CreateImportBody,
  ExportItemsParams,
  ForbiddenResponse,
  GetImportParams,
  ImportDetail,
  ListImports200,
  ListImportsParams,
  NotFoundResponse,
  Problem,
  TooManyRequestsResponse,
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

export const getGetImportTemplateUrl = () => {
  return `/api/v1/content/import-template`;
};

/**
 * @summary Plantilla XLSX de ítems de selección con instrucciones y listas de códigos (R-04)
 */
export const getImportTemplate = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<Blob> => {
  return customInstance<Blob>(getGetImportTemplateUrl(), {
    ...options,
    method: "GET",
  });
};

export const getGetImportTemplateQueryKey = () => {
  return [`/api/v1/content/import-template`] as const;
};

export const getGetImportTemplateQueryOptions = <
  TData = Awaited<ReturnType<typeof getImportTemplate>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportTemplate>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetImportTemplateQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getImportTemplate>>> = ({ signal }) =>
    getImportTemplate({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof getImportTemplate>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type GetImportTemplateQueryResult = NonNullable<
  Awaited<ReturnType<typeof getImportTemplate>>
>;
export type GetImportTemplateQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useGetImportTemplate<
  TData = Awaited<ReturnType<typeof getImportTemplate>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportTemplate>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getImportTemplate>>,
          TError,
          Awaited<ReturnType<typeof getImportTemplate>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetImportTemplate<
  TData = Awaited<ReturnType<typeof getImportTemplate>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportTemplate>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getImportTemplate>>,
          TError,
          Awaited<ReturnType<typeof getImportTemplate>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetImportTemplate<
  TData = Awaited<ReturnType<typeof getImportTemplate>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportTemplate>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Plantilla XLSX de ítems de selección con instrucciones y listas de códigos (R-04)
 */

export function useGetImportTemplate<
  TData = Awaited<ReturnType<typeof getImportTemplate>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportTemplate>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetImportTemplateQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getListImportsUrl = (params?: ListImportsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/imports?${stringifiedParams}`
    : `/api/v1/content/imports`;
};

/**
 * @summary Importaciones recientes (propias; todas para el Administrador)
 */
export const listImports = async (
  params?: ListImportsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<ListImports200> => {
  return customInstance<ListImports200>(getListImportsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getListImportsQueryKey = (params?: ListImportsParams) => {
  return [`/api/v1/content/imports`, ...(params ? [params] : [])] as const;
};

export const getListImportsQueryOptions = <
  TData = Awaited<ReturnType<typeof listImports>>,
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
>(
  params?: ListImportsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listImports>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListImportsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listImports>>> = ({ signal }) =>
    listImports(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listImports>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListImportsQueryResult = NonNullable<Awaited<ReturnType<typeof listImports>>>;
export type ListImportsQueryError =
  UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse;

export function useListImports<
  TData = Awaited<ReturnType<typeof listImports>>,
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
>(
  params: undefined | ListImportsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listImports>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listImports>>,
          TError,
          Awaited<ReturnType<typeof listImports>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListImports<
  TData = Awaited<ReturnType<typeof listImports>>,
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
>(
  params?: ListImportsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listImports>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listImports>>,
          TError,
          Awaited<ReturnType<typeof listImports>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListImports<
  TData = Awaited<ReturnType<typeof listImports>>,
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
>(
  params?: ListImportsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listImports>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Importaciones recientes (propias; todas para el Administrador)
 */

export function useListImports<
  TData = Awaited<ReturnType<typeof listImports>>,
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
>(
  params?: ListImportsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listImports>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListImportsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getCreateImportUrl = () => {
  return `/api/v1/content/imports`;
};

/**
 * @summary Valida un archivo JSON o XLSX y devuelve la vista previa sin guardar ítems (FR-030)
 */
export const createImport = async (
  createImportBody: CreateImportBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<ImportDetail> => {
  const formData = new FormData();
  formData.append(`file`, createImportBody.file);

  return customInstance<ImportDetail>(getCreateImportUrl(), {
    ...options,
    method: "POST",
    body: formData,
  });
};

export const getCreateImportMutationKey = () => ["createImport"] as const;

export const getCreateImportMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | TooManyRequestsResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createImport>>,
    TError,
    CreateImportMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createImport>>,
  TError,
  CreateImportMutationVariables,
  TContext
> => {
  const mutationKey = getCreateImportMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createImport>>,
    CreateImportMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createImport(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateImportMutationResult = NonNullable<Awaited<ReturnType<typeof createImport>>>;
export type CreateImportMutationBody = CreateImportBody;
export type CreateImportMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | TooManyRequestsResponse;
export type CreateImportMutationVariables = { data: CreateImportBody };

/**
 * @summary Valida un archivo JSON o XLSX y devuelve la vista previa sin guardar ítems (FR-030)
 */
export const useCreateImport = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | TooManyRequestsResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createImport>>,
      TError,
      CreateImportMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createImport>>,
  TError,
  CreateImportMutationVariables,
  TContext
> => {
  return useMutation(getCreateImportMutationOptions(options), queryClient);
};
export const getGetImportUrl = (importId: string, params?: GetImportParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/imports/${importId}?${stringifiedParams}`
    : `/api/v1/content/imports/${importId}`;
};

export const getImport = async (
  importId: string,
  params?: GetImportParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<ImportDetail> => {
  return customInstance<ImportDetail>(getGetImportUrl(importId, params), {
    ...options,
    method: "GET",
  });
};

export const getGetImportQueryKey = (importId: string, params?: GetImportParams) => {
  return [`/api/v1/content/imports/${importId}`, ...(params ? [params] : [])] as const;
};

export const getGetImportQueryOptions = <
  TData = Awaited<ReturnType<typeof getImport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
>(
  importId: string,
  params?: GetImportParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImport>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetImportQueryKey(importId, params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getImport>>> = ({ signal }) =>
    getImport(importId, params, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: importId !== null && importId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getImport>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetImportQueryResult = NonNullable<Awaited<ReturnType<typeof getImport>>>;
export type GetImportQueryError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;

export function useGetImport<
  TData = Awaited<ReturnType<typeof getImport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
>(
  importId: string,
  params: undefined | GetImportParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImport>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getImport>>,
          TError,
          Awaited<ReturnType<typeof getImport>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetImport<
  TData = Awaited<ReturnType<typeof getImport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
>(
  importId: string,
  params?: GetImportParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImport>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getImport>>,
          TError,
          Awaited<ReturnType<typeof getImport>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetImport<
  TData = Awaited<ReturnType<typeof getImport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
>(
  importId: string,
  params?: GetImportParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImport>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useGetImport<
  TData = Awaited<ReturnType<typeof getImport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
>(
  importId: string,
  params?: GetImportParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImport>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetImportQueryOptions(importId, params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getGetImportReportUrl = (importId: string) => {
  return `/api/v1/content/imports/${importId}/report`;
};

/**
 * @summary Reporte descargable de los ítems con error (FR-033)
 */
export const getImportReport = async (
  importId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Blob> => {
  return customInstance<Blob>(getGetImportReportUrl(importId), {
    ...options,
    method: "GET",
  });
};

export const getGetImportReportQueryKey = (importId: string) => {
  return [`/api/v1/content/imports/${importId}/report`] as const;
};

export const getGetImportReportQueryOptions = <
  TData = Awaited<ReturnType<typeof getImportReport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  importId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportReport>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetImportReportQueryKey(importId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getImportReport>>> = ({ signal }) =>
    getImportReport(importId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: importId !== null && importId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getImportReport>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetImportReportQueryResult = NonNullable<Awaited<ReturnType<typeof getImportReport>>>;
export type GetImportReportQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useGetImportReport<
  TData = Awaited<ReturnType<typeof getImportReport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  importId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportReport>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getImportReport>>,
          TError,
          Awaited<ReturnType<typeof getImportReport>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetImportReport<
  TData = Awaited<ReturnType<typeof getImportReport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  importId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportReport>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getImportReport>>,
          TError,
          Awaited<ReturnType<typeof getImportReport>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetImportReport<
  TData = Awaited<ReturnType<typeof getImportReport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  importId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportReport>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Reporte descargable de los ítems con error (FR-033)
 */

export function useGetImportReport<
  TData = Awaited<ReturnType<typeof getImportReport>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  importId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getImportReport>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetImportReportQueryOptions(importId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getConfirmImportUrl = (importId: string) => {
  return `/api/v1/content/imports/${importId}/confirmation`;
};

/**
 * @summary Aplica los ítems válidos en una transacción (FR-034 a FR-036)
 */
export const confirmImport = async (
  importId: string,
  confirmImportBody: ConfirmImportBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<ImportDetail> => {
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
  return customInstance<ImportDetail>(getConfirmImportUrl(importId), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(confirmImportBody),
  });
};

export const getConfirmImportMutationKey = () => ["confirmImport"] as const;

export const getConfirmImportMutationOptions = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof confirmImport>>,
    TError,
    ConfirmImportMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof confirmImport>>,
  TError,
  ConfirmImportMutationVariables,
  TContext
> => {
  const mutationKey = getConfirmImportMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof confirmImport>>,
    ConfirmImportMutationVariables
  > = (props) => {
    const { importId, data } = props ?? {};

    return confirmImport(importId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type ConfirmImportMutationResult = NonNullable<Awaited<ReturnType<typeof confirmImport>>>;
export type ConfirmImportMutationBody = ConfirmImportBody;
export type ConfirmImportMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse;
export type ConfirmImportMutationVariables = { importId: string; data: ConfirmImportBody };

/**
 * @summary Aplica los ítems válidos en una transacción (FR-034 a FR-036)
 */
export const useConfirmImport = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof confirmImport>>,
      TError,
      ConfirmImportMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof confirmImport>>,
  TError,
  ConfirmImportMutationVariables,
  TContext
> => {
  return useMutation(getConfirmImportMutationOptions(options), queryClient);
};
export const getExportItemsUrl = (params: ExportItemsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/content/export?${stringifiedParams}`
    : `/api/v1/content/export`;
};

/**
 * @summary Exporta el banco o un filtro en el formato de importación (FR-038, SC-010); 30 por hora por persona
 */
export const exportItems = async (
  params: ExportItemsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<Blob> => {
  return customInstance<Blob>(getExportItemsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getExportItemsQueryKey = (params?: ExportItemsParams) => {
  return [`/api/v1/content/export`, ...(params ? [params] : [])] as const;
};

export const getExportItemsQueryOptions = <
  TData = Awaited<ReturnType<typeof exportItems>>,
  TError =
    UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse | TooManyRequestsResponse,
>(
  params: ExportItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportItems>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getExportItemsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof exportItems>>> = ({ signal }) =>
    exportItems(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof exportItems>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ExportItemsQueryResult = NonNullable<Awaited<ReturnType<typeof exportItems>>>;
export type ExportItemsQueryError =
  UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse | TooManyRequestsResponse;

export function useExportItems<
  TData = Awaited<ReturnType<typeof exportItems>>,
  TError =
    UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse | TooManyRequestsResponse,
>(
  params: ExportItemsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportItems>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof exportItems>>,
          TError,
          Awaited<ReturnType<typeof exportItems>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useExportItems<
  TData = Awaited<ReturnType<typeof exportItems>>,
  TError =
    UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse | TooManyRequestsResponse,
>(
  params: ExportItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportItems>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof exportItems>>,
          TError,
          Awaited<ReturnType<typeof exportItems>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useExportItems<
  TData = Awaited<ReturnType<typeof exportItems>>,
  TError =
    UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse | TooManyRequestsResponse,
>(
  params: ExportItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportItems>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Exporta el banco o un filtro en el formato de importación (FR-038, SC-010); 30 por hora por persona
 */

export function useExportItems<
  TData = Awaited<ReturnType<typeof exportItems>>,
  TError =
    UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse | TooManyRequestsResponse,
>(
  params: ExportItemsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof exportItems>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getExportItemsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
