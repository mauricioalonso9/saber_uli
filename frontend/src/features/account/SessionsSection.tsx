import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { MySession } from "@/api/model";
import {
  getListMySessionsQueryKey,
  useListMySessions,
  useRevokeMyOtherSessions,
  useRevokeMySession,
} from "@/api/me";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { refreshQueries } from "@/shared/api/refresh";
import { formatDateTime } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";

/**
 * Sesiones abiertas (FR-037a, escenario 1.5; ASVS 3.3.4): cada sesión activa con la forma de
 * ingreso, el inicio y la última actividad, sin IP ni dispositivo. Se puede cerrar cualquiera de
 * las otras o todas a la vez; la del dispositivo actual se cierra con "Cerrar sesión".
 */
export function SessionsSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const sessions = useListMySessions();
  const revokeOne = useRevokeMySession();
  const revokeOthers = useRevokeMyOtherSessions();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const title = useId();

  const items = sessions.data?.items ?? [];
  const others = items.filter((session) => !session.current);

  async function run(action: () => Promise<unknown>, done: string) {
    setError(null);
    setNotice(null);
    let ok = true;
    try {
      await action();
    } catch (problem) {
      ok = false;
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
    }
    // También tras un error: la sesión pudo cerrarse desde otro dispositivo.
    await refreshQueries(queryClient, getListMySessionsQueryKey());
    if (ok) setNotice(done);
  }

  function label(session: MySession) {
    return t(`account.sessions.method.${session.auth_method}`);
  }

  return (
    <section aria-labelledby={title} className="mt-8 rounded-md border p-4">
      <h2 id={title} className="mb-2 text-lg font-semibold">
        {t("account.sessions.title")}
      </h2>
      <p className="mb-4">{t("account.sessions.intro")}</p>
      {sessions.isPending ? <p role="status">{t("account.sessions.loading")}</p> : null}
      {notice ? (
        <p role="status" className="mb-4 rounded-md border border-green-300 bg-green-50 p-3">
          {notice}
        </p>
      ) : null}
      {error || sessions.isError ? (
        <p role="alert" className="mb-4 text-destructive">
          {error ?? GENERIC_MESSAGE}
        </p>
      ) : null}

      <ul className="mb-4 flex flex-col gap-3">
        {items.map((session) => (
          <li key={session.id} className="flex flex-col gap-2 rounded-md border p-3">
            <p className="font-medium">
              {label(session)}
              {session.current ? ` (${t("account.sessions.current")})` : ""}
            </p>
            <p className="text-sm">
              {t("account.sessions.started", { date: formatDateTime(session.started_at) })}
              <br />
              {t("account.sessions.lastActivity", {
                date: formatDateTime(session.last_activity_at),
              })}
            </p>
            {session.current ? null : (
              <Button
                variant="outline"
                className="h-11 self-start"
                disabled={revokeOne.isPending}
                aria-label={t("account.sessions.closeOneLabel", {
                  method: label(session),
                  date: formatDateTime(session.last_activity_at),
                })}
                onClick={() =>
                  run(
                    () => revokeOne.mutateAsync({ sessionId: session.id }),
                    t("account.sessions.closedOne"),
                  )
                }
              >
                {t("account.sessions.closeOne")}
              </Button>
            )}
          </li>
        ))}
      </ul>

      {others.length > 0 ? (
        <Button
          variant="outline"
          className="h-11"
          disabled={revokeOthers.isPending}
          onClick={() => run(() => revokeOthers.mutateAsync(), t("account.sessions.closedOthers"))}
        >
          {t("account.sessions.closeOthers")}
        </Button>
      ) : null}
    </section>
  );
}
