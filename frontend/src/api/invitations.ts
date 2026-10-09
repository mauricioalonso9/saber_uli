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
  ConflictResponse,
  ForbiddenResponse,
  Invitation,
  InvitationBatch,
  InvitationInput,
  InvitationPage,
  ListInvitationsParams,
  NotFoundResponse,
  Problem,
  UnauthorizedResponse,
  UpdateInvitationExpiryBody,
  ValidateInvitationBatchBodyTwo,
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

export const getListInvitationsUrl = (params?: ListInvitationsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/invitations?${stringifiedParams}`
    : `/api/v1/invitations`;
};

/**
 * @summary Lista invitaciones (docente solo las suyas; administrador todas) (FR-006)
 */
export const listInvitations = async (
  params?: ListInvitationsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<InvitationPage> => {
  return customInstance<InvitationPage>(getListInvitationsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getListInvitationsQueryKey = (params?: ListInvitationsParams) => {
  return [`/api/v1/invitations`, ...(params ? [params] : [])] as const;
};

export const getListInvitationsQueryOptions = <
  TData = Awaited<ReturnType<typeof listInvitations>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListInvitationsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listInvitations>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getListInvitationsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof listInvitations>>> = ({ signal }) =>
    listInvitations(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof listInvitations>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type ListInvitationsQueryResult = NonNullable<Awaited<ReturnType<typeof listInvitations>>>;
export type ListInvitationsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useListInvitations<
  TData = Awaited<ReturnType<typeof listInvitations>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | ListInvitationsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof listInvitations>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof listInvitations>>,
          TError,
          Awaited<ReturnType<typeof listInvitations>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListInvitations<
  TData = Awaited<ReturnType<typeof listInvitations>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListInvitationsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listInvitations>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof listInvitations>>,
          TError,
          Awaited<ReturnType<typeof listInvitations>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useListInvitations<
  TData = Awaited<ReturnType<typeof listInvitations>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListInvitationsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listInvitations>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Lista invitaciones (docente solo las suyas; administrador todas) (FR-006)
 */

export function useListInvitations<
  TData = Awaited<ReturnType<typeof listInvitations>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: ListInvitationsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof listInvitations>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getListInvitationsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getCreateInvitationUrl = () => {
  return `/api/v1/invitations`;
};

/**
 * @summary Envía una invitación individual (escenario 5.1)
 */
export const createInvitation = async (
  invitationInput: InvitationInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Invitation> => {
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
  return customInstance<Invitation>(getCreateInvitationUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(invitationInput),
  });
};

export const getCreateInvitationMutationKey = () => ["createInvitation"] as const;

export const getCreateInvitationMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof createInvitation>>,
    TError,
    CreateInvitationMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof createInvitation>>,
  TError,
  CreateInvitationMutationVariables,
  TContext
> => {
  const mutationKey = getCreateInvitationMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof createInvitation>>,
    CreateInvitationMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return createInvitation(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type CreateInvitationMutationResult = NonNullable<
  Awaited<ReturnType<typeof createInvitation>>
>;
export type CreateInvitationMutationBody = InvitationInput;
export type CreateInvitationMutationError = UnauthorizedResponse | ForbiddenResponse | Problem;
export type CreateInvitationMutationVariables = { data: InvitationInput };

/**
 * @summary Envía una invitación individual (escenario 5.1)
 */
export const useCreateInvitation = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof createInvitation>>,
      TError,
      CreateInvitationMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof createInvitation>>,
  TError,
  CreateInvitationMutationVariables,
  TContext
> => {
  return useMutation(getCreateInvitationMutationOptions(options), queryClient);
};
export const getGetInvitationUrl = (invitationId: string) => {
  return `/api/v1/invitations/${invitationId}`;
};

export const getInvitation = async (
  invitationId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Invitation> => {
  return customInstance<Invitation>(getGetInvitationUrl(invitationId), {
    ...options,
    method: "GET",
  });
};

export const getGetInvitationQueryKey = (invitationId: string) => {
  return [`/api/v1/invitations/${invitationId}`] as const;
};

export const getGetInvitationQueryOptions = <
  TData = Awaited<ReturnType<typeof getInvitation>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  invitationId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitation>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetInvitationQueryKey(invitationId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getInvitation>>> = ({ signal }) =>
    getInvitation(invitationId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: invitationId !== null && invitationId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getInvitation>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetInvitationQueryResult = NonNullable<Awaited<ReturnType<typeof getInvitation>>>;
export type GetInvitationQueryError = UnauthorizedResponse | NotFoundResponse;

export function useGetInvitation<
  TData = Awaited<ReturnType<typeof getInvitation>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  invitationId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitation>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getInvitation>>,
          TError,
          Awaited<ReturnType<typeof getInvitation>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetInvitation<
  TData = Awaited<ReturnType<typeof getInvitation>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  invitationId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitation>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getInvitation>>,
          TError,
          Awaited<ReturnType<typeof getInvitation>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetInvitation<
  TData = Awaited<ReturnType<typeof getInvitation>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  invitationId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitation>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useGetInvitation<
  TData = Awaited<ReturnType<typeof getInvitation>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  invitationId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitation>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetInvitationQueryOptions(invitationId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getUpdateInvitationExpiryUrl = (invitationId: string) => {
  return `/api/v1/invitations/${invitationId}`;
};

/**
 * @summary Amplía, reduce o renueva el vencimiento del acceso (escenario 5.5)
 */
export const updateInvitationExpiry = async (
  invitationId: string,
  updateInvitationExpiryBody: UpdateInvitationExpiryBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<Invitation> => {
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
  return customInstance<Invitation>(getUpdateInvitationExpiryUrl(invitationId), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(updateInvitationExpiryBody),
  });
};

export const getUpdateInvitationExpiryMutationKey = () => ["updateInvitationExpiry"] as const;

export const getUpdateInvitationExpiryMutationOptions = <
  TError = UnauthorizedResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof updateInvitationExpiry>>,
    TError,
    UpdateInvitationExpiryMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof updateInvitationExpiry>>,
  TError,
  UpdateInvitationExpiryMutationVariables,
  TContext
> => {
  const mutationKey = getUpdateInvitationExpiryMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof updateInvitationExpiry>>,
    UpdateInvitationExpiryMutationVariables
  > = (props) => {
    const { invitationId, data } = props ?? {};

    return updateInvitationExpiry(invitationId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type UpdateInvitationExpiryMutationResult = NonNullable<
  Awaited<ReturnType<typeof updateInvitationExpiry>>
>;
export type UpdateInvitationExpiryMutationBody = UpdateInvitationExpiryBody;
export type UpdateInvitationExpiryMutationError =
  UnauthorizedResponse | NotFoundResponse | Problem | ValidationErrorResponse;
export type UpdateInvitationExpiryMutationVariables = {
  invitationId: string;
  data: UpdateInvitationExpiryBody;
};

/**
 * @summary Amplía, reduce o renueva el vencimiento del acceso (escenario 5.5)
 */
export const useUpdateInvitationExpiry = <
  TError = UnauthorizedResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof updateInvitationExpiry>>,
      TError,
      UpdateInvitationExpiryMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof updateInvitationExpiry>>,
  TError,
  UpdateInvitationExpiryMutationVariables,
  TContext
> => {
  return useMutation(getUpdateInvitationExpiryMutationOptions(options), queryClient);
};
export const getResendInvitationUrl = (invitationId: string) => {
  return `/api/v1/invitations/${invitationId}/resend`;
};

/**
 * @summary Reenvía una invitación no aceptada con un enlace nuevo
 */
export const resendInvitation = async (
  invitationId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Invitation> => {
  return customInstance<Invitation>(getResendInvitationUrl(invitationId), {
    ...options,
    method: "POST",
  });
};

export const getResendInvitationMutationKey = () => ["resendInvitation"] as const;

export const getResendInvitationMutationOptions = <
  TError = UnauthorizedResponse | NotFoundResponse | ConflictResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof resendInvitation>>,
    TError,
    ResendInvitationMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof resendInvitation>>,
  TError,
  ResendInvitationMutationVariables,
  TContext
> => {
  const mutationKey = getResendInvitationMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof resendInvitation>>,
    ResendInvitationMutationVariables
  > = (props) => {
    const { invitationId } = props ?? {};

    return resendInvitation(invitationId, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type ResendInvitationMutationResult = NonNullable<
  Awaited<ReturnType<typeof resendInvitation>>
>;

export type ResendInvitationMutationError =
  UnauthorizedResponse | NotFoundResponse | ConflictResponse;
export type ResendInvitationMutationVariables = { invitationId: string };

/**
 * @summary Reenvía una invitación no aceptada con un enlace nuevo
 */
export const useResendInvitation = <
  TError = UnauthorizedResponse | NotFoundResponse | ConflictResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof resendInvitation>>,
      TError,
      ResendInvitationMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof resendInvitation>>,
  TError,
  ResendInvitationMutationVariables,
  TContext
> => {
  return useMutation(getResendInvitationMutationOptions(options), queryClient);
};
export const getRevokeInvitationUrl = (invitationId: string) => {
  return `/api/v1/invitations/${invitationId}/revocation`;
};

/**
 * @summary Revoca la invitación o el acceso del invitado (escenario 5.4, FR-010)
 */
export const revokeInvitation = async (
  invitationId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Invitation> => {
  return customInstance<Invitation>(getRevokeInvitationUrl(invitationId), {
    ...options,
    method: "POST",
  });
};

export const getRevokeInvitationMutationKey = () => ["revokeInvitation"] as const;

export const getRevokeInvitationMutationOptions = <
  TError = UnauthorizedResponse | NotFoundResponse | ConflictResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof revokeInvitation>>,
    TError,
    RevokeInvitationMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof revokeInvitation>>,
  TError,
  RevokeInvitationMutationVariables,
  TContext
> => {
  const mutationKey = getRevokeInvitationMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof revokeInvitation>>,
    RevokeInvitationMutationVariables
  > = (props) => {
    const { invitationId } = props ?? {};

    return revokeInvitation(invitationId, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type RevokeInvitationMutationResult = NonNullable<
  Awaited<ReturnType<typeof revokeInvitation>>
>;

export type RevokeInvitationMutationError =
  UnauthorizedResponse | NotFoundResponse | ConflictResponse;
export type RevokeInvitationMutationVariables = { invitationId: string };

/**
 * @summary Revoca la invitación o el acceso del invitado (escenario 5.4, FR-010)
 */
export const useRevokeInvitation = <
  TError = UnauthorizedResponse | NotFoundResponse | ConflictResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof revokeInvitation>>,
      TError,
      RevokeInvitationMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof revokeInvitation>>,
  TError,
  RevokeInvitationMutationVariables,
  TContext
> => {
  return useMutation(getRevokeInvitationMutationOptions(options), queryClient);
};
export const getValidateInvitationBatchUrl = () => {
  return `/api/v1/invitation-batches`;
};

/**
 * @summary Valida un lote de invitaciones y devuelve el reporte por fila (FR-009)
 */
export const validateInvitationBatch = async (
  validateInvitationBatchBody: string | ValidateInvitationBatchBodyTwo,
  options?: Parameters<typeof customInstance>[1],
): Promise<InvitationBatch> => {
  return customInstance<InvitationBatch>(getValidateInvitationBatchUrl(), {
    ...options,
    method: "POST",
    body: JSON.stringify(validateInvitationBatchBody),
  });
};

export const getValidateInvitationBatchMutationKey = () => ["validateInvitationBatch"] as const;

export const getValidateInvitationBatchMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof validateInvitationBatch>>,
    TError,
    ValidateInvitationBatchMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof validateInvitationBatch>>,
  TError,
  ValidateInvitationBatchMutationVariables,
  TContext
> => {
  const mutationKey = getValidateInvitationBatchMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof validateInvitationBatch>>,
    ValidateInvitationBatchMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return validateInvitationBatch(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type ValidateInvitationBatchMutationResult = NonNullable<
  Awaited<ReturnType<typeof validateInvitationBatch>>
>;
export type ValidateInvitationBatchMutationBody = string | ValidateInvitationBatchBodyTwo;
export type ValidateInvitationBatchMutationError =
  UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse;
export type ValidateInvitationBatchMutationVariables = {
  data: string | ValidateInvitationBatchBodyTwo;
};

/**
 * @summary Valida un lote de invitaciones y devuelve el reporte por fila (FR-009)
 */
export const useValidateInvitationBatch = <
  TError = UnauthorizedResponse | ForbiddenResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof validateInvitationBatch>>,
      TError,
      ValidateInvitationBatchMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof validateInvitationBatch>>,
  TError,
  ValidateInvitationBatchMutationVariables,
  TContext
> => {
  return useMutation(getValidateInvitationBatchMutationOptions(options), queryClient);
};
export const getGetInvitationBatchUrl = (batchId: string) => {
  return `/api/v1/invitation-batches/${batchId}`;
};

export const getInvitationBatch = async (
  batchId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<InvitationBatch> => {
  return customInstance<InvitationBatch>(getGetInvitationBatchUrl(batchId), {
    ...options,
    method: "GET",
  });
};

export const getGetInvitationBatchQueryKey = (batchId: string) => {
  return [`/api/v1/invitation-batches/${batchId}`] as const;
};

export const getGetInvitationBatchQueryOptions = <
  TData = Awaited<ReturnType<typeof getInvitationBatch>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  batchId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitationBatch>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getGetInvitationBatchQueryKey(batchId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof getInvitationBatch>>> = ({ signal }) =>
    getInvitationBatch(batchId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: batchId !== null && batchId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof getInvitationBatch>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type GetInvitationBatchQueryResult = NonNullable<
  Awaited<ReturnType<typeof getInvitationBatch>>
>;
export type GetInvitationBatchQueryError = UnauthorizedResponse | NotFoundResponse;

export function useGetInvitationBatch<
  TData = Awaited<ReturnType<typeof getInvitationBatch>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  batchId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitationBatch>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof getInvitationBatch>>,
          TError,
          Awaited<ReturnType<typeof getInvitationBatch>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetInvitationBatch<
  TData = Awaited<ReturnType<typeof getInvitationBatch>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  batchId: string,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof getInvitationBatch>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof getInvitationBatch>>,
          TError,
          Awaited<ReturnType<typeof getInvitationBatch>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useGetInvitationBatch<
  TData = Awaited<ReturnType<typeof getInvitationBatch>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  batchId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitationBatch>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useGetInvitationBatch<
  TData = Awaited<ReturnType<typeof getInvitationBatch>>,
  TError = UnauthorizedResponse | NotFoundResponse,
>(
  batchId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof getInvitationBatch>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getGetInvitationBatchQueryOptions(batchId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getConfirmInvitationBatchUrl = (batchId: string) => {
  return `/api/v1/invitation-batches/${batchId}/confirmation`;
};

/**
 * @summary Confirma el lote; crea y envía solo las filas válidas
 */
export const confirmInvitationBatch = async (
  batchId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<InvitationBatch> => {
  return customInstance<InvitationBatch>(getConfirmInvitationBatchUrl(batchId), {
    ...options,
    method: "POST",
  });
};

export const getConfirmInvitationBatchMutationKey = () => ["confirmInvitationBatch"] as const;

export const getConfirmInvitationBatchMutationOptions = <
  TError = UnauthorizedResponse | NotFoundResponse | Problem,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof confirmInvitationBatch>>,
    TError,
    ConfirmInvitationBatchMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof confirmInvitationBatch>>,
  TError,
  ConfirmInvitationBatchMutationVariables,
  TContext
> => {
  const mutationKey = getConfirmInvitationBatchMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof confirmInvitationBatch>>,
    ConfirmInvitationBatchMutationVariables
  > = (props) => {
    const { batchId } = props ?? {};

    return confirmInvitationBatch(batchId, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type ConfirmInvitationBatchMutationResult = NonNullable<
  Awaited<ReturnType<typeof confirmInvitationBatch>>
>;

export type ConfirmInvitationBatchMutationError = UnauthorizedResponse | NotFoundResponse | Problem;
export type ConfirmInvitationBatchMutationVariables = { batchId: string };

/**
 * @summary Confirma el lote; crea y envía solo las filas válidas
 */
export const useConfirmInvitationBatch = <
  TError = UnauthorizedResponse | NotFoundResponse | Problem,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof confirmInvitationBatch>>,
      TError,
      ConfirmInvitationBatchMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof confirmInvitationBatch>>,
  TError,
  ConfirmInvitationBatchMutationVariables,
  TContext
> => {
  return useMutation(getConfirmInvitationBatchMutationOptions(options), queryClient);
};
