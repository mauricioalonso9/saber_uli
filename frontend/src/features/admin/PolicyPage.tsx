import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useRouteContext } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { usePublishPolicyVersion } from "@/api/admin";
import { getGetCurrentPolicyQueryKey, useGetCurrentPolicy } from "@/api/policy";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { formatDate, formatDateTime } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { PolicyMarkdown } from "@/shared/ui/PolicyMarkdown";

/** Mismos límites que el contrato (`publishPolicyVersion`). */
const BODY_MIN = 200;
const BODY_MAX = 100_000;
const TITLE_MAX = 200;
/** Colombia no tiene horario de verano: la vigencia se interpreta siempre en UTC−5. */
const BOGOTA_OFFSET = "-05:00";

function nowInBogota(): string {
  const bogota = new Date(Date.now() - 5 * 60 * 60 * 1000);
  return bogota.toISOString().slice(0, 16); // AAAA-MM-DDTHH:MM para datetime-local
}

function useSchema() {
  const { t } = useTranslation();
  return z.object({
    version: z.string().regex(/^[0-9]+\.[0-9]+$/, t("policyAdmin.errors.version")),
    title: z
      .string()
      .trim()
      .min(1, t("policyAdmin.errors.titleRequired"))
      .max(TITLE_MAX, t("policyAdmin.errors.titleMax", { max: TITLE_MAX })),
    body_markdown: z
      .string()
      .min(BODY_MIN, t("policyAdmin.errors.bodyMin", { min: BODY_MIN }))
      .max(BODY_MAX, t("policyAdmin.errors.bodyMax", { max: BODY_MAX.toLocaleString("es-CO") })),
    effective_from: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/, t("policyAdmin.errors.effectiveFrom")),
  });
}

type PolicyForm = z.infer<ReturnType<typeof useSchema>>;

/**
 * Publicar una versión nueva de la política (FR-017; solo con `policy:publish` y sesión
 * privilegiada). Al empezar a regir, todas las personas deben aceptarla de nuevo, incluido quien
 * la publica.
 */
export function PolicyPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { getSession } = useRouteContext({ from: "__root__" });
  const current = useGetCurrentPolicy();
  const publish = usePublishPolicyVersion();
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ version: string; from: string } | null>(null);
  const ids = { version: useId(), title: useId(), from: useId(), body: useId() };
  const form = useForm<PolicyForm>({
    resolver: zodResolver(useSchema()),
    defaultValues: { version: "", title: "", body_markdown: "", effective_from: nowInBogota() },
  });
  const { errors } = form.formState;
  const body = form.watch("body_markdown");
  const title = form.watch("title");

  async function submit(values: PolicyForm) {
    setError(null);
    setDone(null);
    try {
      const version = await publish.mutateAsync({
        data: { ...values, effective_from: `${values.effective_from}:00${BOGOTA_OFFSET}` },
      });
      setDone({ version: version.version, from: formatDateTime(version.effective_from) });
      form.reset({ ...form.getValues(), version: "", body_markdown: "" });
      setPreview(false);
      await queryClient.invalidateQueries({ queryKey: getGetCurrentPolicyQueryKey() });
      // Quien publica también debe aceptar la versión nueva cuando empiece a regir.
      getSession.invalidate?.();
    } catch (problem) {
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
    }
  }

  const fieldError = (id: string, message?: string) =>
    message ? (
      <p id={`${id}-error`} className="mt-1 text-sm text-destructive">
        {message}
      </p>
    ) : null;

  const describedBy = (id: string, message?: string) => (message ? `${id}-error` : undefined);

  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t("policyAdmin.title")}</h1>
      {current.data ? (
        <p className="mb-4">
          {t("policyAdmin.current", {
            version: current.data.version,
            date: formatDate(current.data.effective_from),
          })}
        </p>
      ) : null}
      <p className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-3">
        {t("policyAdmin.warning")}
      </p>

      {done ? (
        <p role="status" className="mb-4 rounded-md border border-green-300 bg-green-50 p-3">
          {t("policyAdmin.published", done)}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mb-4 text-destructive">
          {error}
        </p>
      ) : null}

      <form onSubmit={(event) => void form.handleSubmit(submit)(event)} noValidate>
        <div className="mb-4 grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor={ids.version}>{t("policyAdmin.version")}</Label>
            <Input
              id={ids.version}
              inputMode="decimal"
              placeholder="2.0"
              aria-invalid={errors.version ? true : undefined}
              aria-describedby={describedBy(ids.version, errors.version?.message)}
              {...form.register("version")}
            />
            {fieldError(ids.version, errors.version?.message)}
          </div>
          <div>
            <Label htmlFor={ids.from}>{t("policyAdmin.effectiveFrom")}</Label>
            <Input
              id={ids.from}
              type="datetime-local"
              aria-invalid={errors.effective_from ? true : undefined}
              aria-describedby={describedBy(ids.from, errors.effective_from?.message)}
              {...form.register("effective_from")}
            />
            {fieldError(ids.from, errors.effective_from?.message)}
          </div>
        </div>
        <div className="mb-4">
          <Label htmlFor={ids.title}>{t("policyAdmin.titleField")}</Label>
          <Input
            id={ids.title}
            maxLength={TITLE_MAX}
            aria-invalid={errors.title ? true : undefined}
            aria-describedby={describedBy(ids.title, errors.title?.message)}
            {...form.register("title")}
          />
          {fieldError(ids.title, errors.title?.message)}
        </div>
        <div className="mb-4">
          <Label htmlFor={ids.body}>{t("policyAdmin.body")}</Label>
          <textarea
            id={ids.body}
            rows={14}
            aria-invalid={errors.body_markdown ? true : undefined}
            aria-describedby={`${ids.body}-count${errors.body_markdown ? ` ${ids.body}-error` : ""}`}
            className="w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            {...form.register("body_markdown")}
          />
          <p id={`${ids.body}-count`} className="text-sm text-muted-foreground">
            {t("policyAdmin.count", {
              count: body.length,
              min: BODY_MIN,
              max: BODY_MAX.toLocaleString("es-CO"),
            })}
          </p>
          {fieldError(ids.body, errors.body_markdown?.message)}
        </div>

        <div className="mb-6 flex flex-col gap-3 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            aria-expanded={preview}
            onClick={() => setPreview((value) => !value)}
          >
            {preview ? t("policyAdmin.hidePreview") : t("policyAdmin.preview")}
          </Button>
          <Button type="submit" disabled={publish.isPending}>
            {t("policyAdmin.publish")}
          </Button>
        </div>
      </form>

      {preview ? (
        <PolicyMarkdown
          title={title.trim() || t("policyAdmin.untitled")}
          markdown={body}
          className="rounded-md border p-4"
        />
      ) : null}
    </section>
  );
}
