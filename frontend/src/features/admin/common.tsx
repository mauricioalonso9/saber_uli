import { useTranslation } from "react-i18next";

import type { AccountStatus, Role } from "@/api/model";
import { startMicrosoftLogin } from "@/features/auth/bootstrap";
import { ApiProblem } from "@/shared/api/http";
import { Button } from "@/shared/ui/button";

export { problemText } from "@/features/invitations/InviteForm";

/** Orden fijo de los roles en pantalla y al guardar. */
export const ROLE_ORDER: Role[] = ["student", "teacher", "program_director", "admin", "guest"];

export function useRoleLabel() {
  const { t } = useTranslation();
  return (role: Role) => t(`admin.roles.${role}`);
}

export function useStatusLabel() {
  const { t } = useTranslation();
  return (status: AccountStatus) => t(`admin.status.${status}`);
}

/**
 * Las pantallas de gestión exigen sesión privilegiada (R-15). Si la API la pide, se ofrece
 * confirmar la identidad con Microsoft y volver a `returnTo`.
 */
export function ReauthAlert({ error, returnTo }: { error: unknown; returnTo: string }) {
  const { t } = useTranslation();
  if (!(error instanceof ApiProblem) || error.slug !== "reauthentication-required") return null;
  return (
    <div role="alert" className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-4">
      <p className="mb-3">{error.message}</p>
      <Button type="button" onClick={() => startMicrosoftLogin(returnTo)}>
        {t("invitations.reauth")}
      </Button>
    </div>
  );
}

export function isReauth(error: unknown): boolean {
  return error instanceof ApiProblem && error.slug === "reauthentication-required";
}

/** Mensajes de éxito y de error de una pantalla de gestión. */
export function Feedback({ message, error }: { message: string | null; error: string | null }) {
  return (
    <>
      {message ? (
        <p role="status" className="mb-4 rounded-md border border-green-300 bg-green-50 p-3">
          {message}
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-red-900"
        >
          {error}
        </p>
      ) : null}
    </>
  );
}
