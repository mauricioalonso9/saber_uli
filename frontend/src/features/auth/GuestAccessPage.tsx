import { Link, useLocation, useRouteContext, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCreateGuestSession } from "@/api/auth";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { Button } from "@/shared/ui/button";

function tokenFrom(hash: string): string | null {
  const value = new URLSearchParams(hash.replace(/^#/, "")).get("t");
  return value && value.length >= 32 ? value : null;
}

/**
 * Ingreso del invitado con el enlace del correo (`/acceso#t=…`; FR-007, R-18).
 *
 * El token viaja en el fragmento: no llega al servidor ni a los registros del proxy. Al abrir la
 * página se borra del historial y solo se envía al pulsar «Ingresar», porque los filtros de
 * seguridad del correo abren los enlaces para analizarlos y no deben gastarlos.
 */
export function GuestAccessPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const location = useLocation();
  const { getSession } = useRouteContext({ from: "__root__" });
  const [token] = useState(() => tokenFrom(location.hash));
  const [error, setError] = useState<string | null>(null);
  const signIn = useCreateGuestSession();

  useEffect(() => {
    if (location.hash) {
      void router.navigate({ to: "/acceso", replace: true });
    }
    // Solo al abrir la página: el token ya quedó en el estado.
  }, []);

  async function enter() {
    if (!token) return;
    setError(null);
    try {
      const tokens = await signIn.mutateAsync({ data: { token } });
      useSessionStore.getState().setSession(tokens.access_token, tokens.expires_in);
    } catch (problem) {
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
      return;
    }
    getSession.invalidate?.();
    await router.navigate({ to: "/" });
  }

  const requestLink = (
    <Link to="/ingresar/invitado" className="underline">
      {t("guestAccess.requestLink")}
    </Link>
  );

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-bold">{t("guestAccess.title")}</h1>
      {token ? (
        <>
          <p>{t("guestAccess.intro")}</p>
          {error ? (
            <div
              role="alert"
              className="rounded-md border border-red-300 bg-red-50 p-4 text-red-900"
            >
              <p className="mb-2">{error}</p>
              {requestLink}
            </div>
          ) : null}
          <Button
            type="button"
            className="h-11 w-full"
            disabled={signIn.isPending}
            onClick={() => void enter()}
          >
            {t("guestAccess.enter")}
          </Button>
        </>
      ) : (
        <>
          <p>{t("guestAccess.noToken")}</p>
          <p>{requestLink}</p>
        </>
      )}
    </section>
  );
}
