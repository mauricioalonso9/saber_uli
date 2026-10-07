import { useQueryClient } from "@tanstack/react-query";
import { useRouteContext, useRouter } from "@tanstack/react-router";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Consent } from "@/api/model";
import { getListMyConsentsQueryKey, useListMyConsents, useRevokeConsent } from "@/api/me";
import { useGetPolicyVersion } from "@/api/policy";
import { clearOfflineSnapshot } from "@/features/auth/offline-access";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { formatDateTime } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { PolicyMarkdown } from "@/shared/ui/PolicyMarkdown";

function problemText(error: unknown): string {
  return error instanceof ApiProblem ? error.message : GENERIC_MESSAGE;
}

function PolicyText({ versionId }: { versionId: string }) {
  const { t } = useTranslation();
  const policy = useGetPolicyVersion(versionId);
  if (policy.isPending) return <p role="status">{t("consent.loading")}</p>;
  if (policy.isError) return <p role="alert">{problemText(policy.error)}</p>;
  return (
    <PolicyMarkdown
      title={policy.data.title}
      markdown={policy.data.body_markdown}
      className="mt-4 max-h-[60vh] overflow-y-auto rounded-md border p-4"
      tabIndex={0}
    />
  );
}

/**
 * Mi autorización de datos (FR-018; escenarios 2.4 y 2.5): versión aceptada, fecha, texto de esa
 * versión, historial y revocación con confirmación. Revocar cierra todas las sesiones en el
 * servidor; aquí se borran además el token en memoria y la instantánea sin conexión.
 */
export function ConsentSettingsPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { getSession } = useRouteContext({ from: "__root__" });
  const consents = useListMyConsents();
  const revoke = useRevokeConsent();
  const [showText, setShowText] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [revoked, setRevoked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const ids = {
    current: useId(),
    history: useId(),
    confirmTitle: useId(),
    confirmBody: useId(),
    done: useId(),
  };

  useEffect(() => {
    if (confirming) confirmButton.current?.focus();
  }, [confirming]);

  const decisionText = (consent: Consent) =>
    t(`consentSettings.decision.${consent.decision}`, {
      version: consent.policy_version,
      date: formatDateTime(consent.decided_at),
    });

  async function confirmRevocation() {
    setError(null);
    try {
      await revoke.mutateAsync();
    } catch (problem) {
      setError(problemText(problem));
      setConfirming(false);
      return;
    }
    // El servidor ya cerró las sesiones: se borra todo lo local.
    useSessionStore.getState().clear();
    await clearOfflineSnapshot();
    getSession.invalidate?.();
    queryClient.removeQueries({ queryKey: getListMyConsentsQueryKey() });
    setConfirming(false);
    setRevoked(true);
  }

  if (revoked) {
    return (
      <section>
        <h1 className="mb-4 text-2xl font-bold">{t("consentSettings.title")}</h1>
        <div role="status" aria-labelledby={ids.done} className="rounded-md border p-4">
          <h2 id={ids.done} className="mb-2 text-lg font-semibold">
            {t("consentSettings.revoked.title")}
          </h2>
          <p className="mb-4">{t("consentSettings.revoked.body")}</p>
          <Button type="button" onClick={() => void router.navigate({ to: "/ingresar" })}>
            {t("consentSettings.revoked.signInAgain")}
          </Button>
        </div>
      </section>
    );
  }

  const current = consents.data?.current ?? null;

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("consentSettings.title")}</h1>
      {consents.isPending ? <p role="status">{t("consent.loading")}</p> : null}
      {consents.isError ? <p role="alert">{problemText(consents.error)}</p> : null}
      {error ? (
        <p role="alert" className="mb-4 text-destructive">
          {error}
        </p>
      ) : null}

      {consents.data ? (
        <>
          <section aria-labelledby={ids.current} className="mb-6">
            <h2 id={ids.current} className="mb-2 text-lg font-semibold">
              {t("consentSettings.current")}
            </h2>
            {current ? (
              <>
                <p className="mb-3">
                  {t("consentSettings.acceptedOn", {
                    version: current.policy_version,
                    date: formatDateTime(current.decided_at),
                  })}
                </p>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button
                    type="button"
                    variant="outline"
                    aria-expanded={showText}
                    onClick={() => setShowText((value) => !value)}
                  >
                    {showText
                      ? t("consentSettings.hideText", { version: current.policy_version })
                      : t("consentSettings.showText", { version: current.policy_version })}
                  </Button>
                  <Button type="button" variant="destructive" onClick={() => setConfirming(true)}>
                    {t("consentSettings.revoke")}
                  </Button>
                </div>
                {showText ? <PolicyText versionId={current.policy_version_id} /> : null}
              </>
            ) : (
              <p>{t("consentSettings.none")}</p>
            )}
          </section>

          {confirming ? (
            <div
              role="alertdialog"
              aria-labelledby={ids.confirmTitle}
              aria-describedby={ids.confirmBody}
              className="mb-6 rounded-md border border-destructive p-4"
            >
              <h2 id={ids.confirmTitle} className="mb-2 text-lg font-semibold">
                {t("consentSettings.confirm.title")}
              </h2>
              <p id={ids.confirmBody} className="mb-4">
                {t("consentSettings.confirm.body")}
              </p>
              <div className="flex gap-3">
                <Button
                  ref={confirmButton}
                  type="button"
                  variant="destructive"
                  disabled={revoke.isPending}
                  onClick={() => void confirmRevocation()}
                >
                  {t("consentSettings.confirm.yes")}
                </Button>
                <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
                  {t("consentSettings.confirm.cancel")}
                </Button>
              </div>
            </div>
          ) : null}

          <h2 id={ids.history} className="mb-2 text-lg font-semibold">
            {t("consentSettings.history")}
          </h2>
          <ul aria-labelledby={ids.history} className="list-disc pl-6">
            {consents.data.items.map((consent) => (
              <li key={consent.id}>{decisionText(consent)}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
