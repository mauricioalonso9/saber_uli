import { Link, getRouteApi } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { startMicrosoftLogin } from "@/features/auth/bootstrap";
import { Button } from "@/shared/ui/button";

const route = getRouteApi("/ingresar");

/** Códigos de `/ingresar?error=` que devuelve el backend (T078). */
const KNOWN_ERRORS = new Set([
  "tenant_not_allowed",
  "idp_unavailable",
  "invalid_state",
  "login_cancelled",
  "login_failed",
  "account_disabled",
  "account_deleted",
]);

/** Ingreso con la cuenta institucional (FR-001) y alternativa para invitados (SC-008). */
export function LoginPage() {
  const { t } = useTranslation();
  const { error, return_to: returnTo } = route.useSearch();
  const errorKey = error ? (KNOWN_ERRORS.has(error) ? error : "unknown") : null;

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-bold">{t("login.title")}</h1>
      {errorKey ? (
        <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 text-red-900">
          {t(`login.errors.${errorKey}`)}
        </div>
      ) : null}
      <p>{t("login.intro")}</p>
      <Button type="button" className="w-full" onClick={() => startMicrosoftLogin(returnTo)}>
        {t("login.microsoft")}
      </Button>
      <p className="text-sm">
        <Link to="/acceso" className="underline">
          {t("login.guestLink")}
        </Link>
      </p>
    </section>
  );
}
