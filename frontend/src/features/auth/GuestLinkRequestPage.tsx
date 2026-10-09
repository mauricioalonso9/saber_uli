import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "@tanstack/react-router";
import { useId, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { useRequestGuestSignInLink } from "@/api/auth";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

const EMAIL = /^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$/;

/**
 * Un invitado pide un enlace de ingreso nuevo (FR-013, `/ingresar/invitado`). La respuesta es la
 * misma exista o no el correo: la página nunca revela si alguien está invitado.
 */
export function GuestLinkRequestPage() {
  const { t } = useTranslation();
  const request = useRequestGuestSignInLink();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const emailId = useId();
  const schema = useMemo(
    () =>
      z.object({
        email: z.string().trim().max(254).regex(EMAIL, t("guestLink.errors.email")),
      }),
    [t],
  );
  const form = useForm<{ email: string }>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });
  const emailError = form.formState.errors.email?.message;

  async function submit({ email }: { email: string }) {
    setError(null);
    setSent(false);
    try {
      await request.mutateAsync({ data: { email: email.trim() } });
    } catch (problem) {
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
      return;
    }
    setSent(true);
  }

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-bold">{t("guestLink.title")}</h1>
      <p>{t("guestLink.intro")}</p>
      {sent ? (
        <p role="status" className="rounded-md border border-green-300 bg-green-50 p-4">
          {t("guestLink.sent")}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 text-red-900">
          {error}
        </p>
      ) : null}
      <form
        noValidate
        onSubmit={(event) => void form.handleSubmit(submit)(event)}
        className="space-y-4"
      >
        <div>
          <Label htmlFor={emailId}>{t("guestLink.email")}</Label>
          <Input
            id={emailId}
            type="email"
            autoComplete="email"
            inputMode="email"
            className="h-11"
            aria-invalid={emailError ? true : undefined}
            aria-describedby={emailError ? `${emailId}-error` : undefined}
            {...form.register("email")}
          />
          {emailError ? (
            <p id={`${emailId}-error`} className="mt-1 text-sm text-destructive">
              {emailError}
            </p>
          ) : null}
        </div>
        <Button type="submit" className="h-11 w-full" disabled={request.isPending}>
          {t("guestLink.submit")}
        </Button>
      </form>
      <p className="text-sm">
        <Link to="/ingresar" className="underline">
          {t("guestLink.back")}
        </Link>
      </p>
    </section>
  );
}
