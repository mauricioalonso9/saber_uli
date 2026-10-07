import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import type { InvitationInput } from "@/api/model";
import { useCreateInvitation } from "@/api/invitations";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

const EMAIL = /^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$/;

/** Hoy en Colombia como AAAA-MM-DD (comparable con el valor de un `<input type="date">`). */
export function todayInBogota(): string {
  return new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

/** El acceso dura hasta el final del día elegido, en hora de Colombia. */
export function endOfDayInBogota(day: string): string {
  return `${day}T23:59:59-05:00`;
}

/** Mensaje de un rechazo del servidor: el detalle dice, por ejemplo, el plazo máximo. */
export function problemText(problem: unknown): string {
  if (!(problem instanceof ApiProblem)) return GENERIC_MESSAGE;
  return problem.status === 422 && problem.detail ? problem.detail : problem.message;
}

interface Values {
  email: string;
  invitee_name: string;
  access_until: string;
}

/**
 * Invitar a una persona externa (FR-006; escenario 5.1). El plazo máximo del docente (FR-006a)
 * y el rechazo de correos institucionales (FR-008) los decide el servidor; aquí se muestra su
 * explicación. Sin fecha, el acceso usa el plazo por defecto de los parámetros.
 */
export function InviteForm({ onCreated }: { onCreated: () => void }) {
  const { t } = useTranslation();
  const create = useCreateInvitation();
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const ids = { title: useId(), email: useId(), name: useId(), until: useId() };
  const schema = useMemo(
    () =>
      z.object({
        email: z.string().trim().max(254).regex(EMAIL, t("invitations.form.errors.email")),
        invitee_name: z.string().trim().max(120),
        access_until: z
          .string()
          .refine((value) => !value || value > todayInBogota(), t("invitations.form.errors.date")),
      }),
    [t],
  );
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", invitee_name: "", access_until: "" },
  });
  const { errors } = form.formState;

  async function submit(values: Values) {
    setError(null);
    setSent(null);
    const body: InvitationInput = { email: values.email.trim() };
    if (values.invitee_name.trim()) body.invitee_name = values.invitee_name.trim();
    if (values.access_until) body.access_expires_at = endOfDayInBogota(values.access_until);
    try {
      await create.mutateAsync({ data: body });
    } catch (problem) {
      setError(problemText(problem));
      return;
    }
    setSent(t("invitations.form.sent", { email: body.email }));
    form.reset();
    onCreated();
  }

  const described = (id: string, failed: boolean) => (failed ? `${id}-error` : undefined);
  const fieldError = (id: string, message?: string) =>
    message ? (
      <p id={`${id}-error`} className="mt-1 text-sm text-destructive">
        {message}
      </p>
    ) : null;

  return (
    <section className="mb-8">
      {sent ? (
        <p role="status" className="mb-3 rounded-md border border-green-300 bg-green-50 p-3">
          {sent}
        </p>
      ) : null}
      <form
        aria-labelledby={ids.title}
        noValidate
        onSubmit={(event) => void form.handleSubmit(submit)(event)}
        className="space-y-4 rounded-md border p-4"
      >
        <h2 id={ids.title} className="text-lg font-semibold">
          {t("invitations.form.title")}
        </h2>
        {error ? (
          <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
            {error}
          </p>
        ) : null}
        <div>
          <Label htmlFor={ids.email}>{t("invitations.form.email")}</Label>
          <Input
            id={ids.email}
            type="email"
            autoComplete="off"
            className="h-11"
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={described(ids.email, Boolean(errors.email))}
            {...form.register("email")}
          />
          {fieldError(ids.email, errors.email?.message)}
        </div>
        <div>
          <Label htmlFor={ids.name}>{t("invitations.form.name")}</Label>
          <Input
            id={ids.name}
            className="h-11"
            maxLength={120}
            {...form.register("invitee_name")}
          />
        </div>
        <div>
          <Label htmlFor={ids.until}>{t("invitations.form.until")}</Label>
          <Input
            id={ids.until}
            type="date"
            className="h-11"
            aria-invalid={errors.access_until ? true : undefined}
            aria-describedby={described(ids.until, Boolean(errors.access_until))}
            {...form.register("access_until")}
          />
          {fieldError(ids.until, errors.access_until?.message)}
        </div>
        <Button type="submit" className="h-11" disabled={create.isPending}>
          {t("invitations.form.submit")}
        </Button>
      </form>
    </section>
  );
}
