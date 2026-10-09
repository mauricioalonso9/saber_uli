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
  AdminListAuditEventsParams,
  AdminListDeletionRequestsParams,
  AdminListGroupMembersParams,
  AdminListGroupsParams,
  AdminListProgramsParams,
  AdminListUsersParams,
  AdminSetUserRolesBody,
  AdminUpdateUserStatusBody,
  AdminUser,
  AdminUserPage,
  AuditEventPage,
  ConflictResponse,
  DeletionRequestPage,
  ForbiddenResponse,
  Group,
  GroupInput,
  GroupMemberPage,
  GroupPage,
  GroupPatch,
  NotFoundResponse,
  PolicyVersion,
  Problem,
  Program,
  ProgramInput,
  ProgramPage,
  ProgramPatch,
  PublishPolicyVersionBody,
  Settings,
  SettingsPatch,
  UnauthorizedResponse,
  UserIdList,
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

export const getPublishPolicyVersionUrl = () => {
  return `/api/v1/admin/privacy-policy/versions`;
};

/**
 * @summary Publica una nueva versión; exige nueva aceptación a todos (FR-017)
 */
export const publishPolicyVersion = async (
  publishPolicyVersionBody: PublishPolicyVersionBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<PolicyVersion> => {
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
  return customInstance<PolicyVersion>(getPublishPolicyVersionUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(publishPolicyVersionBody),
  });
};

export const getPublishPolicyVersionMutationKey = () => ["publishPolicyVersion"] as const;

export const getPublishPolicyVersionMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | ConflictResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof publishPolicyVersion>>,
    TError,
    PublishPolicyVersionMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof publishPolicyVersion>>,
  TError,
  PublishPolicyVersionMutationVariables,
  TContext
> => {
  const mutationKey = getPublishPolicyVersionMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof publishPolicyVersion>>,
    PublishPolicyVersionMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return publishPolicyVersion(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type PublishPolicyVersionMutationResult = NonNullable<
  Awaited<ReturnType<typeof publishPolicyVersion>>
>;
export type PublishPolicyVersionMutationBody = PublishPolicyVersionBody;
export type PublishPolicyVersionMutationError =
  UnauthorizedResponse | ForbiddenResponse | ConflictResponse | ValidationErrorResponse;
export type PublishPolicyVersionMutationVariables = { data: PublishPolicyVersionBody };

/**
 * @summary Publica una nueva versión; exige nueva aceptación a todos (FR-017)
 */
export const usePublishPolicyVersion = <
  TError = UnauthorizedResponse | ForbiddenResponse | ConflictResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof publishPolicyVersion>>,
      TError,
      PublishPolicyVersionMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof publishPolicyVersion>>,
  TError,
  PublishPolicyVersionMutationVariables,
  TContext
> => {
  return useMutation(getPublishPolicyVersionMutationOptions(options), queryClient);
};
export const getAdminListProgramsUrl = (params?: AdminListProgramsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/admin/programs?${stringifiedParams}`
    : `/api/v1/admin/programs`;
};

export const adminListPrograms = async (
  params?: AdminListProgramsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<ProgramPage> => {
  return customInstance<ProgramPage>(getAdminListProgramsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getAdminListProgramsQueryKey = (params?: AdminListProgramsParams) => {
  return [`/api/v1/admin/programs`, ...(params ? [params] : [])] as const;
};

export const getAdminListProgramsQueryOptions = <
  TData = Awaited<ReturnType<typeof adminListPrograms>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListProgramsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListPrograms>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminListProgramsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminListPrograms>>> = ({ signal }) =>
    adminListPrograms(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof adminListPrograms>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type AdminListProgramsQueryResult = NonNullable<
  Awaited<ReturnType<typeof adminListPrograms>>
>;
export type AdminListProgramsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useAdminListPrograms<
  TData = Awaited<ReturnType<typeof adminListPrograms>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | AdminListProgramsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListPrograms>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListPrograms>>,
          TError,
          Awaited<ReturnType<typeof adminListPrograms>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListPrograms<
  TData = Awaited<ReturnType<typeof adminListPrograms>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListProgramsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListPrograms>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListPrograms>>,
          TError,
          Awaited<ReturnType<typeof adminListPrograms>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListPrograms<
  TData = Awaited<ReturnType<typeof adminListPrograms>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListProgramsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListPrograms>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useAdminListPrograms<
  TData = Awaited<ReturnType<typeof adminListPrograms>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListProgramsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListPrograms>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminListProgramsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminCreateProgramUrl = () => {
  return `/api/v1/admin/programs`;
};

/**
 * @summary Crea un programa (FR-028)
 */
export const adminCreateProgram = async (
  programInput: ProgramInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Program> => {
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
  return customInstance<Program>(getAdminCreateProgramUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(programInput),
  });
};

export const getAdminCreateProgramMutationKey = () => ["adminCreateProgram"] as const;

export const getAdminCreateProgramMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | ConflictResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminCreateProgram>>,
    TError,
    AdminCreateProgramMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminCreateProgram>>,
  TError,
  AdminCreateProgramMutationVariables,
  TContext
> => {
  const mutationKey = getAdminCreateProgramMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminCreateProgram>>,
    AdminCreateProgramMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return adminCreateProgram(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminCreateProgramMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminCreateProgram>>
>;
export type AdminCreateProgramMutationBody = ProgramInput;
export type AdminCreateProgramMutationError =
  UnauthorizedResponse | ForbiddenResponse | ConflictResponse | ValidationErrorResponse;
export type AdminCreateProgramMutationVariables = { data: ProgramInput };

/**
 * @summary Crea un programa (FR-028)
 */
export const useAdminCreateProgram = <
  TError = UnauthorizedResponse | ForbiddenResponse | ConflictResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminCreateProgram>>,
      TError,
      AdminCreateProgramMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminCreateProgram>>,
  TError,
  AdminCreateProgramMutationVariables,
  TContext
> => {
  return useMutation(getAdminCreateProgramMutationOptions(options), queryClient);
};
export const getAdminUpdateProgramUrl = (programId: string) => {
  return `/api/v1/admin/programs/${programId}`;
};

export const adminUpdateProgram = async (
  programId: string,
  programPatch: ProgramPatch,
  options?: Parameters<typeof customInstance>[1],
): Promise<Program> => {
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
  return customInstance<Program>(getAdminUpdateProgramUrl(programId), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(programPatch),
  });
};

export const getAdminUpdateProgramMutationKey = () => ["adminUpdateProgram"] as const;

export const getAdminUpdateProgramMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminUpdateProgram>>,
    TError,
    AdminUpdateProgramMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminUpdateProgram>>,
  TError,
  AdminUpdateProgramMutationVariables,
  TContext
> => {
  const mutationKey = getAdminUpdateProgramMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminUpdateProgram>>,
    AdminUpdateProgramMutationVariables
  > = (props) => {
    const { programId, data } = props ?? {};

    return adminUpdateProgram(programId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminUpdateProgramMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminUpdateProgram>>
>;
export type AdminUpdateProgramMutationBody = ProgramPatch;
export type AdminUpdateProgramMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;
export type AdminUpdateProgramMutationVariables = { programId: string; data: ProgramPatch };

export const useAdminUpdateProgram = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminUpdateProgram>>,
      TError,
      AdminUpdateProgramMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminUpdateProgram>>,
  TError,
  AdminUpdateProgramMutationVariables,
  TContext
> => {
  return useMutation(getAdminUpdateProgramMutationOptions(options), queryClient);
};
export const getAdminListUsersUrl = (params?: AdminListUsersParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/admin/users?${stringifiedParams}`
    : `/api/v1/admin/users`;
};

export const adminListUsers = async (
  params?: AdminListUsersParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<AdminUserPage> => {
  return customInstance<AdminUserPage>(getAdminListUsersUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getAdminListUsersQueryKey = (params?: AdminListUsersParams) => {
  return [`/api/v1/admin/users`, ...(params ? [params] : [])] as const;
};

export const getAdminListUsersQueryOptions = <
  TData = Awaited<ReturnType<typeof adminListUsers>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListUsersParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListUsers>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminListUsersQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminListUsers>>> = ({ signal }) =>
    adminListUsers(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof adminListUsers>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type AdminListUsersQueryResult = NonNullable<Awaited<ReturnType<typeof adminListUsers>>>;
export type AdminListUsersQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useAdminListUsers<
  TData = Awaited<ReturnType<typeof adminListUsers>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | AdminListUsersParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListUsers>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListUsers>>,
          TError,
          Awaited<ReturnType<typeof adminListUsers>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListUsers<
  TData = Awaited<ReturnType<typeof adminListUsers>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListUsersParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListUsers>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListUsers>>,
          TError,
          Awaited<ReturnType<typeof adminListUsers>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListUsers<
  TData = Awaited<ReturnType<typeof adminListUsers>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListUsersParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListUsers>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useAdminListUsers<
  TData = Awaited<ReturnType<typeof adminListUsers>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListUsersParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListUsers>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminListUsersQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminGetUserUrl = (userId: string) => {
  return `/api/v1/admin/users/${userId}`;
};

export const adminGetUser = async (
  userId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<AdminUser> => {
  return customInstance<AdminUser>(getAdminGetUserUrl(userId), {
    ...options,
    method: "GET",
  });
};

export const getAdminGetUserQueryKey = (userId: string) => {
  return [`/api/v1/admin/users/${userId}`] as const;
};

export const getAdminGetUserQueryOptions = <
  TData = Awaited<ReturnType<typeof adminGetUser>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  userId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetUser>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminGetUserQueryKey(userId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminGetUser>>> = ({ signal }) =>
    adminGetUser(userId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: userId !== null && userId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof adminGetUser>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type AdminGetUserQueryResult = NonNullable<Awaited<ReturnType<typeof adminGetUser>>>;
export type AdminGetUserQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useAdminGetUser<
  TData = Awaited<ReturnType<typeof adminGetUser>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  userId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetUser>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminGetUser>>,
          TError,
          Awaited<ReturnType<typeof adminGetUser>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminGetUser<
  TData = Awaited<ReturnType<typeof adminGetUser>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  userId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetUser>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminGetUser>>,
          TError,
          Awaited<ReturnType<typeof adminGetUser>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminGetUser<
  TData = Awaited<ReturnType<typeof adminGetUser>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  userId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetUser>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useAdminGetUser<
  TData = Awaited<ReturnType<typeof adminGetUser>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  userId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetUser>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminGetUserQueryOptions(userId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminUpdateUserStatusUrl = (userId: string) => {
  return `/api/v1/admin/users/${userId}`;
};

/**
 * @summary Desactiva o reactiva una cuenta (FR-029)
 */
export const adminUpdateUserStatus = async (
  userId: string,
  adminUpdateUserStatusBody: AdminUpdateUserStatusBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<AdminUser> => {
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
  return customInstance<AdminUser>(getAdminUpdateUserStatusUrl(userId), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(adminUpdateUserStatusBody),
  });
};

export const getAdminUpdateUserStatusMutationKey = () => ["adminUpdateUserStatus"] as const;

export const getAdminUpdateUserStatusMutationOptions = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminUpdateUserStatus>>,
    TError,
    AdminUpdateUserStatusMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminUpdateUserStatus>>,
  TError,
  AdminUpdateUserStatusMutationVariables,
  TContext
> => {
  const mutationKey = getAdminUpdateUserStatusMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminUpdateUserStatus>>,
    AdminUpdateUserStatusMutationVariables
  > = (props) => {
    const { userId, data } = props ?? {};

    return adminUpdateUserStatus(userId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminUpdateUserStatusMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminUpdateUserStatus>>
>;
export type AdminUpdateUserStatusMutationBody = AdminUpdateUserStatusBody;
export type AdminUpdateUserStatusMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse;
export type AdminUpdateUserStatusMutationVariables = {
  userId: string;
  data: AdminUpdateUserStatusBody;
};

/**
 * @summary Desactiva o reactiva una cuenta (FR-029)
 */
export const useAdminUpdateUserStatus = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminUpdateUserStatus>>,
      TError,
      AdminUpdateUserStatusMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminUpdateUserStatus>>,
  TError,
  AdminUpdateUserStatusMutationVariables,
  TContext
> => {
  return useMutation(getAdminUpdateUserStatusMutationOptions(options), queryClient);
};
export const getAdminSetUserRolesUrl = (userId: string) => {
  return `/api/v1/admin/users/${userId}/roles`;
};

/**
 * @summary Define los roles y programas dirigidos de un usuario (FR-023…FR-026)
 */
export const adminSetUserRoles = async (
  userId: string,
  adminSetUserRolesBody: AdminSetUserRolesBody,
  options?: Parameters<typeof customInstance>[1],
): Promise<AdminUser> => {
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
  return customInstance<AdminUser>(getAdminSetUserRolesUrl(userId), {
    ...options,
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(adminSetUserRolesBody),
  });
};

export const getAdminSetUserRolesMutationKey = () => ["adminSetUserRoles"] as const;

export const getAdminSetUserRolesMutationOptions = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminSetUserRoles>>,
    TError,
    AdminSetUserRolesMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminSetUserRoles>>,
  TError,
  AdminSetUserRolesMutationVariables,
  TContext
> => {
  const mutationKey = getAdminSetUserRolesMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminSetUserRoles>>,
    AdminSetUserRolesMutationVariables
  > = (props) => {
    const { userId, data } = props ?? {};

    return adminSetUserRoles(userId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminSetUserRolesMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminSetUserRoles>>
>;
export type AdminSetUserRolesMutationBody = AdminSetUserRolesBody;
export type AdminSetUserRolesMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse;
export type AdminSetUserRolesMutationVariables = { userId: string; data: AdminSetUserRolesBody };

/**
 * @summary Define los roles y programas dirigidos de un usuario (FR-023…FR-026)
 */
export const useAdminSetUserRoles = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminSetUserRoles>>,
      TError,
      AdminSetUserRolesMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminSetUserRoles>>,
  TError,
  AdminSetUserRolesMutationVariables,
  TContext
> => {
  return useMutation(getAdminSetUserRolesMutationOptions(options), queryClient);
};
export const getAdminListGroupsUrl = (params?: AdminListGroupsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/admin/groups?${stringifiedParams}`
    : `/api/v1/admin/groups`;
};

export const adminListGroups = async (
  params?: AdminListGroupsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<GroupPage> => {
  return customInstance<GroupPage>(getAdminListGroupsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getAdminListGroupsQueryKey = (params?: AdminListGroupsParams) => {
  return [`/api/v1/admin/groups`, ...(params ? [params] : [])] as const;
};

export const getAdminListGroupsQueryOptions = <
  TData = Awaited<ReturnType<typeof adminListGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListGroupsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListGroups>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminListGroupsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminListGroups>>> = ({ signal }) =>
    adminListGroups(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof adminListGroups>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type AdminListGroupsQueryResult = NonNullable<Awaited<ReturnType<typeof adminListGroups>>>;
export type AdminListGroupsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useAdminListGroups<
  TData = Awaited<ReturnType<typeof adminListGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | AdminListGroupsParams,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListGroups>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListGroups>>,
          TError,
          Awaited<ReturnType<typeof adminListGroups>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListGroups<
  TData = Awaited<ReturnType<typeof adminListGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListGroupsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListGroups>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListGroups>>,
          TError,
          Awaited<ReturnType<typeof adminListGroups>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListGroups<
  TData = Awaited<ReturnType<typeof adminListGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListGroupsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListGroups>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useAdminListGroups<
  TData = Awaited<ReturnType<typeof adminListGroups>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListGroupsParams,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminListGroups>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminListGroupsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminCreateGroupUrl = () => {
  return `/api/v1/admin/groups`;
};

export const adminCreateGroup = async (
  groupInput: GroupInput,
  options?: Parameters<typeof customInstance>[1],
): Promise<Group> => {
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
  return customInstance<Group>(getAdminCreateGroupUrl(), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(groupInput),
  });
};

export const getAdminCreateGroupMutationKey = () => ["adminCreateGroup"] as const;

export const getAdminCreateGroupMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminCreateGroup>>,
    TError,
    AdminCreateGroupMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminCreateGroup>>,
  TError,
  AdminCreateGroupMutationVariables,
  TContext
> => {
  const mutationKey = getAdminCreateGroupMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminCreateGroup>>,
    AdminCreateGroupMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return adminCreateGroup(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminCreateGroupMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminCreateGroup>>
>;
export type AdminCreateGroupMutationBody = GroupInput;
export type AdminCreateGroupMutationError =
  UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse;
export type AdminCreateGroupMutationVariables = { data: GroupInput };

export const useAdminCreateGroup = <
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminCreateGroup>>,
      TError,
      AdminCreateGroupMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminCreateGroup>>,
  TError,
  AdminCreateGroupMutationVariables,
  TContext
> => {
  return useMutation(getAdminCreateGroupMutationOptions(options), queryClient);
};
export const getAdminGetGroupUrl = (groupId: string) => {
  return `/api/v1/admin/groups/${groupId}`;
};

export const adminGetGroup = async (
  groupId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<Group> => {
  return customInstance<Group>(getAdminGetGroupUrl(groupId), {
    ...options,
    method: "GET",
  });
};

export const getAdminGetGroupQueryKey = (groupId: string) => {
  return [`/api/v1/admin/groups/${groupId}`] as const;
};

export const getAdminGetGroupQueryOptions = <
  TData = Awaited<ReturnType<typeof adminGetGroup>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetGroup>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminGetGroupQueryKey(groupId);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminGetGroup>>> = ({ signal }) =>
    adminGetGroup(groupId, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: groupId !== null && groupId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof adminGetGroup>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type AdminGetGroupQueryResult = NonNullable<Awaited<ReturnType<typeof adminGetGroup>>>;
export type AdminGetGroupQueryError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useAdminGetGroup<
  TData = Awaited<ReturnType<typeof adminGetGroup>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetGroup>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminGetGroup>>,
          TError,
          Awaited<ReturnType<typeof adminGetGroup>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminGetGroup<
  TData = Awaited<ReturnType<typeof adminGetGroup>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetGroup>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminGetGroup>>,
          TError,
          Awaited<ReturnType<typeof adminGetGroup>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminGetGroup<
  TData = Awaited<ReturnType<typeof adminGetGroup>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetGroup>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useAdminGetGroup<
  TData = Awaited<ReturnType<typeof adminGetGroup>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetGroup>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminGetGroupQueryOptions(groupId, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminUpdateGroupUrl = (groupId: string) => {
  return `/api/v1/admin/groups/${groupId}`;
};

export const adminUpdateGroup = async (
  groupId: string,
  groupPatch: GroupPatch,
  options?: Parameters<typeof customInstance>[1],
): Promise<Group> => {
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
  return customInstance<Group>(getAdminUpdateGroupUrl(groupId), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(groupPatch),
  });
};

export const getAdminUpdateGroupMutationKey = () => ["adminUpdateGroup"] as const;

export const getAdminUpdateGroupMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminUpdateGroup>>,
    TError,
    AdminUpdateGroupMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminUpdateGroup>>,
  TError,
  AdminUpdateGroupMutationVariables,
  TContext
> => {
  const mutationKey = getAdminUpdateGroupMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminUpdateGroup>>,
    AdminUpdateGroupMutationVariables
  > = (props) => {
    const { groupId, data } = props ?? {};

    return adminUpdateGroup(groupId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminUpdateGroupMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminUpdateGroup>>
>;
export type AdminUpdateGroupMutationBody = GroupPatch;
export type AdminUpdateGroupMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse;
export type AdminUpdateGroupMutationVariables = { groupId: string; data: GroupPatch };

export const useAdminUpdateGroup = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminUpdateGroup>>,
      TError,
      AdminUpdateGroupMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminUpdateGroup>>,
  TError,
  AdminUpdateGroupMutationVariables,
  TContext
> => {
  return useMutation(getAdminUpdateGroupMutationOptions(options), queryClient);
};
export const getAdminListGroupMembersUrl = (
  groupId: string,
  params?: AdminListGroupMembersParams,
) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/admin/groups/${groupId}/members?${stringifiedParams}`
    : `/api/v1/admin/groups/${groupId}/members`;
};

/**
 * @summary Miembros de un grupo para el administrador (nombre y correo) (FR-027)
 */
export const adminListGroupMembers = async (
  groupId: string,
  params?: AdminListGroupMembersParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<GroupMemberPage> => {
  return customInstance<GroupMemberPage>(getAdminListGroupMembersUrl(groupId, params), {
    ...options,
    method: "GET",
  });
};

export const getAdminListGroupMembersQueryKey = (
  groupId: string,
  params?: AdminListGroupMembersParams,
) => {
  return [`/api/v1/admin/groups/${groupId}/members`, ...(params ? [params] : [])] as const;
};

export const getAdminListGroupMembersQueryOptions = <
  TData = Awaited<ReturnType<typeof adminListGroupMembers>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: AdminListGroupMembersParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListGroupMembers>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminListGroupMembersQueryKey(groupId, params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminListGroupMembers>>> = ({ signal }) =>
    adminListGroupMembers(groupId, params, { signal, ...requestOptions });

  return {
    queryKey,
    queryFn,
    enabled: groupId !== null && groupId !== undefined,
    ...queryOptions,
  } as UseQueryOptions<Awaited<ReturnType<typeof adminListGroupMembers>>, TError, TData> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };
};

export type AdminListGroupMembersQueryResult = NonNullable<
  Awaited<ReturnType<typeof adminListGroupMembers>>
>;
export type AdminListGroupMembersQueryError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;

export function useAdminListGroupMembers<
  TData = Awaited<ReturnType<typeof adminListGroupMembers>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params: undefined | AdminListGroupMembersParams,
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListGroupMembers>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListGroupMembers>>,
          TError,
          Awaited<ReturnType<typeof adminListGroupMembers>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListGroupMembers<
  TData = Awaited<ReturnType<typeof adminListGroupMembers>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: AdminListGroupMembersParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListGroupMembers>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListGroupMembers>>,
          TError,
          Awaited<ReturnType<typeof adminListGroupMembers>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListGroupMembers<
  TData = Awaited<ReturnType<typeof adminListGroupMembers>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: AdminListGroupMembersParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListGroupMembers>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Miembros de un grupo para el administrador (nombre y correo) (FR-027)
 */

export function useAdminListGroupMembers<
  TData = Awaited<ReturnType<typeof adminListGroupMembers>>,
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
>(
  groupId: string,
  params?: AdminListGroupMembersParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListGroupMembers>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminListGroupMembersQueryOptions(groupId, params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminAddGroupMembersUrl = (groupId: string) => {
  return `/api/v1/admin/groups/${groupId}/members`;
};

export const adminAddGroupMembers = async (
  groupId: string,
  userIdList: UserIdList,
  options?: Parameters<typeof customInstance>[1],
): Promise<Group> => {
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
  return customInstance<Group>(getAdminAddGroupMembersUrl(groupId), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(userIdList),
  });
};

export const getAdminAddGroupMembersMutationKey = () => ["adminAddGroupMembers"] as const;

export const getAdminAddGroupMembersMutationOptions = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminAddGroupMembers>>,
    TError,
    AdminAddGroupMembersMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminAddGroupMembers>>,
  TError,
  AdminAddGroupMembersMutationVariables,
  TContext
> => {
  const mutationKey = getAdminAddGroupMembersMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminAddGroupMembers>>,
    AdminAddGroupMembersMutationVariables
  > = (props) => {
    const { groupId, data } = props ?? {};

    return adminAddGroupMembers(groupId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminAddGroupMembersMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminAddGroupMembers>>
>;
export type AdminAddGroupMembersMutationBody = UserIdList;
export type AdminAddGroupMembersMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse;
export type AdminAddGroupMembersMutationVariables = { groupId: string; data: UserIdList };

export const useAdminAddGroupMembers = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminAddGroupMembers>>,
      TError,
      AdminAddGroupMembersMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminAddGroupMembers>>,
  TError,
  AdminAddGroupMembersMutationVariables,
  TContext
> => {
  return useMutation(getAdminAddGroupMembersMutationOptions(options), queryClient);
};
export const getAdminRemoveGroupMemberUrl = (groupId: string, userId: string) => {
  return `/api/v1/admin/groups/${groupId}/members/${userId}`;
};

export const adminRemoveGroupMember = async (
  groupId: string,
  userId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<void> => {
  return customInstance<void>(getAdminRemoveGroupMemberUrl(groupId, userId), {
    ...options,
    method: "DELETE",
  });
};

export const getAdminRemoveGroupMemberMutationKey = () => ["adminRemoveGroupMember"] as const;

export const getAdminRemoveGroupMemberMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminRemoveGroupMember>>,
    TError,
    AdminRemoveGroupMemberMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminRemoveGroupMember>>,
  TError,
  AdminRemoveGroupMemberMutationVariables,
  TContext
> => {
  const mutationKey = getAdminRemoveGroupMemberMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminRemoveGroupMember>>,
    AdminRemoveGroupMemberMutationVariables
  > = (props) => {
    const { groupId, userId } = props ?? {};

    return adminRemoveGroupMember(groupId, userId, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminRemoveGroupMemberMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminRemoveGroupMember>>
>;

export type AdminRemoveGroupMemberMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;
export type AdminRemoveGroupMemberMutationVariables = { groupId: string; userId: string };

export const useAdminRemoveGroupMember = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminRemoveGroupMember>>,
      TError,
      AdminRemoveGroupMemberMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminRemoveGroupMember>>,
  TError,
  AdminRemoveGroupMemberMutationVariables,
  TContext
> => {
  return useMutation(getAdminRemoveGroupMemberMutationOptions(options), queryClient);
};
export const getAdminAddGroupTeachersUrl = (groupId: string) => {
  return `/api/v1/admin/groups/${groupId}/teachers`;
};

export const adminAddGroupTeachers = async (
  groupId: string,
  userIdList: UserIdList,
  options?: Parameters<typeof customInstance>[1],
): Promise<Group> => {
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
  return customInstance<Group>(getAdminAddGroupTeachersUrl(groupId), {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(userIdList),
  });
};

export const getAdminAddGroupTeachersMutationKey = () => ["adminAddGroupTeachers"] as const;

export const getAdminAddGroupTeachersMutationOptions = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminAddGroupTeachers>>,
    TError,
    AdminAddGroupTeachersMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminAddGroupTeachers>>,
  TError,
  AdminAddGroupTeachersMutationVariables,
  TContext
> => {
  const mutationKey = getAdminAddGroupTeachersMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminAddGroupTeachers>>,
    AdminAddGroupTeachersMutationVariables
  > = (props) => {
    const { groupId, data } = props ?? {};

    return adminAddGroupTeachers(groupId, data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminAddGroupTeachersMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminAddGroupTeachers>>
>;
export type AdminAddGroupTeachersMutationBody = UserIdList;
export type AdminAddGroupTeachersMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse;
export type AdminAddGroupTeachersMutationVariables = { groupId: string; data: UserIdList };

export const useAdminAddGroupTeachers = <
  TError =
    UnauthorizedResponse | ForbiddenResponse | NotFoundResponse | Problem | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminAddGroupTeachers>>,
      TError,
      AdminAddGroupTeachersMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminAddGroupTeachers>>,
  TError,
  AdminAddGroupTeachersMutationVariables,
  TContext
> => {
  return useMutation(getAdminAddGroupTeachersMutationOptions(options), queryClient);
};
export const getAdminRemoveGroupTeacherUrl = (groupId: string, userId: string) => {
  return `/api/v1/admin/groups/${groupId}/teachers/${userId}`;
};

export const adminRemoveGroupTeacher = async (
  groupId: string,
  userId: string,
  options?: Parameters<typeof customInstance>[1],
): Promise<void> => {
  return customInstance<void>(getAdminRemoveGroupTeacherUrl(groupId, userId), {
    ...options,
    method: "DELETE",
  });
};

export const getAdminRemoveGroupTeacherMutationKey = () => ["adminRemoveGroupTeacher"] as const;

export const getAdminRemoveGroupTeacherMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminRemoveGroupTeacher>>,
    TError,
    AdminRemoveGroupTeacherMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminRemoveGroupTeacher>>,
  TError,
  AdminRemoveGroupTeacherMutationVariables,
  TContext
> => {
  const mutationKey = getAdminRemoveGroupTeacherMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminRemoveGroupTeacher>>,
    AdminRemoveGroupTeacherMutationVariables
  > = (props) => {
    const { groupId, userId } = props ?? {};

    return adminRemoveGroupTeacher(groupId, userId, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminRemoveGroupTeacherMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminRemoveGroupTeacher>>
>;

export type AdminRemoveGroupTeacherMutationError =
  UnauthorizedResponse | ForbiddenResponse | NotFoundResponse;
export type AdminRemoveGroupTeacherMutationVariables = { groupId: string; userId: string };

export const useAdminRemoveGroupTeacher = <
  TError = UnauthorizedResponse | ForbiddenResponse | NotFoundResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminRemoveGroupTeacher>>,
      TError,
      AdminRemoveGroupTeacherMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminRemoveGroupTeacher>>,
  TError,
  AdminRemoveGroupTeacherMutationVariables,
  TContext
> => {
  return useMutation(getAdminRemoveGroupTeacherMutationOptions(options), queryClient);
};
export const getAdminListDeletionRequestsUrl = (params?: AdminListDeletionRequestsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/admin/deletion-requests?${stringifiedParams}`
    : `/api/v1/admin/deletion-requests`;
};

/**
 * @summary Solicitudes de supresión con estado y fecha límite (FR-034)
 */
export const adminListDeletionRequests = async (
  params?: AdminListDeletionRequestsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<DeletionRequestPage> => {
  return customInstance<DeletionRequestPage>(getAdminListDeletionRequestsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getAdminListDeletionRequestsQueryKey = (params?: AdminListDeletionRequestsParams) => {
  return [`/api/v1/admin/deletion-requests`, ...(params ? [params] : [])] as const;
};

export const getAdminListDeletionRequestsQueryOptions = <
  TData = Awaited<ReturnType<typeof adminListDeletionRequests>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListDeletionRequestsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListDeletionRequests>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminListDeletionRequestsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminListDeletionRequests>>> = ({
    signal,
  }) => adminListDeletionRequests(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof adminListDeletionRequests>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type AdminListDeletionRequestsQueryResult = NonNullable<
  Awaited<ReturnType<typeof adminListDeletionRequests>>
>;
export type AdminListDeletionRequestsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useAdminListDeletionRequests<
  TData = Awaited<ReturnType<typeof adminListDeletionRequests>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | AdminListDeletionRequestsParams,
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListDeletionRequests>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListDeletionRequests>>,
          TError,
          Awaited<ReturnType<typeof adminListDeletionRequests>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListDeletionRequests<
  TData = Awaited<ReturnType<typeof adminListDeletionRequests>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListDeletionRequestsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListDeletionRequests>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListDeletionRequests>>,
          TError,
          Awaited<ReturnType<typeof adminListDeletionRequests>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListDeletionRequests<
  TData = Awaited<ReturnType<typeof adminListDeletionRequests>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListDeletionRequestsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListDeletionRequests>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Solicitudes de supresión con estado y fecha límite (FR-034)
 */

export function useAdminListDeletionRequests<
  TData = Awaited<ReturnType<typeof adminListDeletionRequests>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListDeletionRequestsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListDeletionRequests>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminListDeletionRequestsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminGetSettingsUrl = () => {
  return `/api/v1/admin/settings`;
};

export const adminGetSettings = async (
  options?: Parameters<typeof customInstance>[1],
): Promise<Settings> => {
  return customInstance<Settings>(getAdminGetSettingsUrl(), {
    ...options,
    method: "GET",
  });
};

export const getAdminGetSettingsQueryKey = () => {
  return [`/api/v1/admin/settings`] as const;
};

export const getAdminGetSettingsQueryOptions = <
  TData = Awaited<ReturnType<typeof adminGetSettings>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(options?: {
  query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetSettings>>, TError, TData>>;
  request?: SecondParameter<typeof customInstance>;
}) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminGetSettingsQueryKey();

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminGetSettings>>> = ({ signal }) =>
    adminGetSettings({ signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof adminGetSettings>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type AdminGetSettingsQueryResult = NonNullable<Awaited<ReturnType<typeof adminGetSettings>>>;
export type AdminGetSettingsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useAdminGetSettings<
  TData = Awaited<ReturnType<typeof adminGetSettings>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options: {
    query: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetSettings>>, TError, TData>> &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminGetSettings>>,
          TError,
          Awaited<ReturnType<typeof adminGetSettings>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminGetSettings<
  TData = Awaited<ReturnType<typeof adminGetSettings>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetSettings>>, TError, TData>> &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminGetSettings>>,
          TError,
          Awaited<ReturnType<typeof adminGetSettings>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminGetSettings<
  TData = Awaited<ReturnType<typeof adminGetSettings>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetSettings>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };

export function useAdminGetSettings<
  TData = Awaited<ReturnType<typeof adminGetSettings>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  options?: {
    query?: Partial<UseQueryOptions<Awaited<ReturnType<typeof adminGetSettings>>, TError, TData>>;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminGetSettingsQueryOptions(options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}

export const getAdminUpdateSettingsUrl = () => {
  return `/api/v1/admin/settings`;
};

/**
 * @summary Ajusta parámetros como el plazo máximo de docentes (FR-006a)
 */
export const adminUpdateSettings = async (
  settingsPatch: SettingsPatch,
  options?: Parameters<typeof customInstance>[1],
): Promise<Settings> => {
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
  return customInstance<Settings>(getAdminUpdateSettingsUrl(), {
    ...options,
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getHeaders(options?.headers) },
    body: JSON.stringify(settingsPatch),
  });
};

export const getAdminUpdateSettingsMutationKey = () => ["adminUpdateSettings"] as const;

export const getAdminUpdateSettingsMutationOptions = <
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
  TContext = unknown,
>(options?: {
  mutation?: UseMutationOptions<
    Awaited<ReturnType<typeof adminUpdateSettings>>,
    TError,
    AdminUpdateSettingsMutationVariables,
    TContext
  >;
  request?: SecondParameter<typeof customInstance>;
}): UseMutationOptions<
  Awaited<ReturnType<typeof adminUpdateSettings>>,
  TError,
  AdminUpdateSettingsMutationVariables,
  TContext
> => {
  const mutationKey = getAdminUpdateSettingsMutationKey();
  const { mutation: mutationOptions, request: requestOptions } = options
    ? options.mutation && "mutationKey" in options.mutation && options.mutation.mutationKey
      ? options
      : { ...options, mutation: { ...options.mutation, mutationKey } }
    : { mutation: { mutationKey }, request: undefined };

  const mutationFn: MutationFunction<
    Awaited<ReturnType<typeof adminUpdateSettings>>,
    AdminUpdateSettingsMutationVariables
  > = (props) => {
    const { data } = props ?? {};

    return adminUpdateSettings(data, requestOptions);
  };

  return { mutationFn, ...mutationOptions };
};

export type AdminUpdateSettingsMutationResult = NonNullable<
  Awaited<ReturnType<typeof adminUpdateSettings>>
>;
export type AdminUpdateSettingsMutationBody = SettingsPatch;
export type AdminUpdateSettingsMutationError =
  UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse;
export type AdminUpdateSettingsMutationVariables = { data: SettingsPatch };

/**
 * @summary Ajusta parámetros como el plazo máximo de docentes (FR-006a)
 */
export const useAdminUpdateSettings = <
  TError = UnauthorizedResponse | ForbiddenResponse | ValidationErrorResponse,
  TContext = unknown,
>(
  options?: {
    mutation?: UseMutationOptions<
      Awaited<ReturnType<typeof adminUpdateSettings>>,
      TError,
      AdminUpdateSettingsMutationVariables,
      TContext
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseMutationResult<
  Awaited<ReturnType<typeof adminUpdateSettings>>,
  TError,
  AdminUpdateSettingsMutationVariables,
  TContext
> => {
  return useMutation(getAdminUpdateSettingsMutationOptions(options), queryClient);
};
export const getAdminListAuditEventsUrl = (params?: AdminListAuditEventsParams) => {
  const normalizedParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) {
      normalizedParams.append(key, value === null ? "null" : String(value));
    }
  });

  const stringifiedParams = normalizedParams.toString();

  return stringifiedParams.length > 0
    ? `/api/v1/admin/audit-events?${stringifiedParams}`
    : `/api/v1/admin/audit-events`;
};

/**
 * @summary Consulta de auditoría, solo lectura (FR-035)
 */
export const adminListAuditEvents = async (
  params?: AdminListAuditEventsParams,
  options?: Parameters<typeof customInstance>[1],
): Promise<AuditEventPage> => {
  return customInstance<AuditEventPage>(getAdminListAuditEventsUrl(params), {
    ...options,
    method: "GET",
  });
};

export const getAdminListAuditEventsQueryKey = (params?: AdminListAuditEventsParams) => {
  return [`/api/v1/admin/audit-events`, ...(params ? [params] : [])] as const;
};

export const getAdminListAuditEventsQueryOptions = <
  TData = Awaited<ReturnType<typeof adminListAuditEvents>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListAuditEventsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListAuditEvents>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
) => {
  const { query: queryOptions, request: requestOptions } = options ?? {};

  const queryKey = queryOptions?.queryKey ?? getAdminListAuditEventsQueryKey(params);

  const queryFn: QueryFunction<Awaited<ReturnType<typeof adminListAuditEvents>>> = ({ signal }) =>
    adminListAuditEvents(params, { signal, ...requestOptions });

  return { queryKey, queryFn, ...queryOptions } as UseQueryOptions<
    Awaited<ReturnType<typeof adminListAuditEvents>>,
    TError,
    TData
  > & { queryKey: DataTag<QueryKey, TData, TError> };
};

export type AdminListAuditEventsQueryResult = NonNullable<
  Awaited<ReturnType<typeof adminListAuditEvents>>
>;
export type AdminListAuditEventsQueryError = UnauthorizedResponse | ForbiddenResponse;

export function useAdminListAuditEvents<
  TData = Awaited<ReturnType<typeof adminListAuditEvents>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params: undefined | AdminListAuditEventsParams,
  options: {
    query: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListAuditEvents>>, TError, TData>
    > &
      Pick<
        DefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListAuditEvents>>,
          TError,
          Awaited<ReturnType<typeof adminListAuditEvents>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): DefinedUseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListAuditEvents<
  TData = Awaited<ReturnType<typeof adminListAuditEvents>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListAuditEventsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListAuditEvents>>, TError, TData>
    > &
      Pick<
        UndefinedInitialDataOptions<
          Awaited<ReturnType<typeof adminListAuditEvents>>,
          TError,
          Awaited<ReturnType<typeof adminListAuditEvents>>
        >,
        "initialData"
      >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
export function useAdminListAuditEvents<
  TData = Awaited<ReturnType<typeof adminListAuditEvents>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListAuditEventsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListAuditEvents>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> };
/**
 * @summary Consulta de auditoría, solo lectura (FR-035)
 */

export function useAdminListAuditEvents<
  TData = Awaited<ReturnType<typeof adminListAuditEvents>>,
  TError = UnauthorizedResponse | ForbiddenResponse,
>(
  params?: AdminListAuditEventsParams,
  options?: {
    query?: Partial<
      UseQueryOptions<Awaited<ReturnType<typeof adminListAuditEvents>>, TError, TData>
    >;
    request?: SecondParameter<typeof customInstance>;
  },
  queryClient?: QueryClient,
): UseQueryResult<TData, TError> & { queryKey: DataTag<QueryKey, TData, TError> } {
  const queryOptions = getAdminListAuditEventsQueryOptions(params, options);

  const query = useQuery(queryOptions, queryClient) as UseQueryResult<TData, TError> & {
    queryKey: DataTag<QueryKey, TData, TError>;
  };

  return withQueryKey(query, queryOptions.queryKey);
}
