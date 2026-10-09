import { useRouteContext } from "@tanstack/react-router";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { DeletionRequest } from "@/api/model";
import { useRequestMyDeletion } from "@/api/me";
import { clearOfflineSnapshot } from "@/features/auth/offline-access";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { formatDay } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

const CONFIRMATION = "ELIMINAR";

/**
 * Solicitar la supresión de la cuenta (FR-032; escenarios 7.1, 7.2 y 7.5): explica qué se borra
 * y qué se conserva sin identificar, y exige escribir ELIMINAR. El servidor cierra las sesiones;
 * aquí se borra lo local.
 */
export function DeleteAccountSection() {
  const { t } = useTranslation();
  const { getSession } = useRouteContext({ from: "__root__" });
  const request = useRequestMyDeletion();
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<DeletionRequest | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const ids = {
    title: useId(),
    confirmTitle: useId(),
    confirmBody: useId(),
    input: useId(),
    done: useId(),
  };

  useEffect(() => {
    if (confirming) input.current?.focus();
  }, [confirming]);

  function close() {
    setConfirming(false);
    setTyped("");
  }

  async function confirm() {
    setError(null);
    let created: DeletionRequest;
    try {
      created = await request.mutateAsync({ data: { confirmation: CONFIRMATION } });
    } catch (problem) {
      setError(
        problem instanceof ApiProblem
          ? problem.slug === "last-admin"
            ? t("account.deletion.lastAdmin")
            : problem.message
          : GENERIC_MESSAGE,
      );
      close();
      return;
    }
    useSessionStore.getState().clear();
    await clearOfflineSnapshot();
    getSession.invalidate?.();
    close();
    setDone(created);
  }

  if (done) {
    return (
      <div role="status" aria-labelledby={ids.done} className="mt-8 rounded-md border p-4">
        <h2 id={ids.done} className="mb-2 text-lg font-semibold">
          {t("account.deletion.done.title")}
        </h2>
        <p>{t("account.deletion.done.body", { date: formatDay(done.due_date) })}</p>
      </div>
    );
  }

  return (
    <section aria-labelledby={ids.title} className="mt-8 rounded-md border border-destructive p-4">
      <h2 id={ids.title} className="mb-2 text-lg font-semibold">
        {t("account.deletion.title")}
      </h2>
      <p className="mb-2">{t("account.deletion.intro")}</p>
      <ul className="mb-2 list-disc pl-6">
        <li>{t("account.deletion.erased")}</li>
        <li>{t("account.deletion.kept")}</li>
      </ul>
      <p className="mb-4">{t("account.deletion.irreversible")}</p>
      {error ? (
        <p role="alert" className="mb-4 text-destructive">
          {error}
        </p>
      ) : null}

      {confirming ? (
        <div
          role="alertdialog"
          aria-labelledby={ids.confirmTitle}
          aria-describedby={ids.confirmBody}
          className="rounded-md border p-4"
        >
          <h3 id={ids.confirmTitle} className="mb-2 font-semibold">
            {t("account.deletion.confirm.title")}
          </h3>
          <p id={ids.confirmBody} className="mb-3">
            {t("account.deletion.confirm.body")}
          </p>
          <Label htmlFor={ids.input}>{t("account.deletion.confirm.label")}</Label>
          <Input
            ref={input}
            id={ids.input}
            autoComplete="off"
            className="mb-4 mt-1 h-11"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
          />
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="destructive"
              disabled={typed !== CONFIRMATION || request.isPending}
              onClick={() => void confirm()}
            >
              {t("account.deletion.confirm.yes")}
            </Button>
            <Button type="button" variant="outline" onClick={close}>
              {t("account.deletion.confirm.cancel")}
            </Button>
          </div>
        </div>
      ) : (
        <Button type="button" variant="destructive" onClick={() => setConfirming(true)}>
          {t("account.deletion.open")}
        </Button>
      )}
    </section>
  );
}
