import { useRouteContext, useRouter } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCreateLocalSession } from "@/api/auth";
import { useSessionStore } from "@/features/auth/session-store";
import { ApiProblem } from "@/shared/api/http";
import { Button } from "@/shared/ui/button";

const INPUT = "mt-1 block h-11 w-full rounded-md border border-input bg-background px-3";

/**
 * Ingreso de la cuenta local de administración con usuario y contraseña (US9; FR-040, FR-044).
 * Va plegado: la comunidad ingresa con Microsoft y los invitados con su enlace.
 */
export function LocalLoginForm() {
  const { t } = useTranslation();
  const id = useId();
  const router = useRouter();
  const { getSession } = useRouteContext({ from: "__root__" });
  const signIn = useCreateLocalSession();
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      const tokens = await signIn.mutateAsync({ data: { username: username.trim(), password } });
      useSessionStore.getState().setSession(tokens.access_token, tokens.expires_in);
    } catch (problem) {
      setError(
        problem instanceof ApiProblem
          ? (problem.detail ?? problem.message)
          : t("localLogin.failed"),
      );
      return;
    } finally {
      setPassword("");
    }
    getSession.invalidate?.();
    await router.navigate({ to: "/" });
  }

  return (
    <div className="space-y-3 border-t pt-4">
      <Button
        type="button"
        variant="outline"
        aria-expanded={open}
        aria-controls={`${id}-form`}
        onClick={() => setOpen((value) => !value)}
      >
        {t("localLogin.toggle")}
      </Button>
      {open ? (
        <form
          id={`${id}-form`}
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <p className="text-sm text-muted-foreground">{t("localLogin.intro")}</p>
          {error ? (
            <div
              role="alert"
              className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900"
            >
              {error}
            </div>
          ) : null}
          <div>
            <label htmlFor={`${id}-user`}>{t("localLogin.username")}</label>
            <input
              id={`${id}-user`}
              className={INPUT}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
              maxLength={64}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor={`${id}-password`}>{t("localLogin.password")}</label>
            <input
              id={`${id}-password`}
              type="password"
              className={INPUT}
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <Button type="submit" className="w-full" disabled={signIn.isPending}>
            {t("localLogin.submit")}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
