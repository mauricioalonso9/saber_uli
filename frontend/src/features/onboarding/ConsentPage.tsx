import { Link, useRouteContext, useRouter } from "@tanstack/react-router";
import { type FormEvent, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ConsentDecision } from "@/api/model";
import { useDecideConsent } from "@/api/me";
import { useGetCurrentPolicy } from "@/api/policy";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { formatDate } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { PolicyMarkdown } from "@/shared/ui/PolicyMarkdown";

type Choice = Exclude<ConsentDecision, "revoked">;

/**
 * Autorización de tratamiento de datos en el primer ingreso (FR-014 a FR-016; escenarios 2.1 a
 * 2.3). Muestra la versión vigente y pide una decisión explícita: ninguna opción viene marcada.
 * Si la persona no acepta, se le explica que no puede usar la plataforma y se le ofrece aceptar
 * más adelante o solicitar la eliminación de su cuenta.
 */
export function ConsentPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { getSession } = useRouteContext({ from: "__root__" });
  const policy = useGetCurrentPolicy();
  const decide = useDecideConsent();
  const [choice, setChoice] = useState<Choice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rejected, setRejected] = useState(false);
  const decisionLabel = useId();
  const rejectedTitle = useId();
  const firstOption = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!choice) {
      setError(t("consent.chooseOne"));
      return;
    }
    if (!policy.data) return;
    setError(null);
    try {
      await decide.mutateAsync({
        data: { policy_version_id: policy.data.id, decision: choice },
      });
    } catch (problem) {
      if (problem instanceof ApiProblem && problem.slug === "policy-version-not-current") {
        setChoice(null);
        void policy.refetch();
      }
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
      return;
    }
    if (choice === "accepted") {
      getSession.invalidate?.();
      await router.navigate({ to: "/inicio" });
    } else {
      setRejected(true);
    }
  }

  function reviewAgain() {
    setRejected(false);
    setChoice(null);
    // Tras volver, el foco queda en la primera opción.
    requestAnimationFrame(() => firstOption.current?.focus());
  }

  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t("consent.title")}</h1>
      <p className="mb-4">{t("consent.intro")}</p>

      {policy.isPending ? <p role="status">{t("consent.loading")}</p> : null}
      {policy.isError ? (
        <p role="alert" className="text-destructive">
          {policy.error instanceof ApiProblem ? policy.error.message : GENERIC_MESSAGE}
        </p>
      ) : null}

      {policy.data ? (
        <>
          <p className="mb-2 text-sm text-muted-foreground">
            {t("consent.version", {
              version: policy.data.version,
              date: formatDate(policy.data.effective_from),
            })}
          </p>
          <PolicyMarkdown
            title={policy.data.title}
            markdown={policy.data.body_markdown}
            className="mb-6 max-h-[60vh] overflow-y-auto rounded-md border p-4"
            tabIndex={0}
          />
        </>
      ) : null}

      {rejected ? (
        <section
          aria-labelledby={rejectedTitle}
          className="rounded-md border border-amber-300 bg-amber-50 p-4"
        >
          <h2 id={rejectedTitle} className="mb-2 text-lg font-semibold">
            {t("consent.rejected.title")}
          </h2>
          <p className="mb-4">{t("consent.rejected.body")}</p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button type="button" onClick={reviewAgain}>
              {t("consent.rejected.reviewAgain")}
            </Button>
            <Link to="/mi-cuenta/datos" className="self-center underline">
              {t("consent.rejected.requestDeletion")}
            </Link>
          </div>
        </section>
      ) : policy.data ? (
        <form onSubmit={(event) => void submit(event)} noValidate>
          <div role="radiogroup" aria-labelledby={decisionLabel} className="mb-4">
            <p id={decisionLabel} className="mb-2 font-semibold">
              {t("consent.decision")}
            </p>
            <label className="mb-2 flex min-h-11 items-center gap-3">
              <input
                ref={firstOption}
                type="radio"
                name="decision"
                value="accepted"
                checked={choice === "accepted"}
                onChange={() => setChoice("accepted")}
                className="size-5"
              />
              {t("consent.accept")}
            </label>
            <label className="flex min-h-11 items-center gap-3">
              <input
                type="radio"
                name="decision"
                value="rejected"
                checked={choice === "rejected"}
                onChange={() => setChoice("rejected")}
                className="size-5"
              />
              {t("consent.reject")}
            </label>
          </div>
          {error ? (
            <p role="alert" className="mb-4 text-destructive">
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={decide.isPending}>
            {t("consent.confirm")}
          </Button>
        </form>
      ) : null}
    </section>
  );
}
