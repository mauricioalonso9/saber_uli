import { useRouteContext, useRouter } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useChangeLocalPassword } from "@/api/auth";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem } from "@/shared/api/http";
import { Button } from "@/shared/ui/button";

const MIN_LENGTH = 12;
const MAX_LENGTH = 128;
const INPUT = "mt-1 block h-11 w-full rounded-md border border-input bg-background px-3";

/**
 * Cambio obligatorio de la contraseña de la cuenta local (US9; FR-041, FR-042, FR-045). El
 * servidor aplica la política completa; aquí se adelantan la longitud y la repetición.
 */
export function ChangePasswordPage() {
  const { t } = useTranslation();
  const id = useId();
  const router = useRouter();
  const { getSession } = useRouteContext({ from: "__root__" });
  const change = useChangeLocalPassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (next !== repeat) {
      setError(t("changePassword.mismatch"));
      return;
    }
    if (next.length < MIN_LENGTH) {
      setError(t("changePassword.tooShort", { count: MIN_LENGTH }));
      return;
    }
    try {
      const tokens = await change.mutateAsync({
        data: { current_password: current, new_password: next },
      });
      useSessionStore.getState().setSession(tokens.access_token, tokens.expires_in);
    } catch (problem) {
      setError(
        problem instanceof ApiProblem
          ? (problem.detail ?? problem.message)
          : t("changePassword.failed"),
      );
      return;
    }
    setCurrent("");
    setNext("");
    setRepeat("");
    getSession.invalidate?.();
    await router.navigate({ to: "/inicio" });
  }

  const field = (
    key: string,
    label: string,
    value: string,
    set: (value: string) => void,
    autoComplete: string,
  ) => (
    <div>
      <label htmlFor={`${id}-${key}`}>{label}</label>
      <input
        id={`${id}-${key}`}
        type="password"
        className={INPUT}
        autoComplete={autoComplete}
        required
        maxLength={MAX_LENGTH}
        value={value}
        onChange={(event) => set(event.target.value)}
      />
    </div>
  );

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-bold">{t("changePassword.title")}</h1>
      <p>{t("changePassword.intro", { count: MIN_LENGTH })}</p>
      {error ? (
        <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {error}
        </div>
      ) : null}
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        {field("current", t("changePassword.current"), current, setCurrent, "current-password")}
        {field("next", t("changePassword.next"), next, setNext, "new-password")}
        {field("repeat", t("changePassword.repeat"), repeat, setRepeat, "new-password")}
        <Button type="submit" className="w-full" disabled={change.isPending}>
          {t("changePassword.submit")}
        </Button>
      </form>
    </section>
  );
}
