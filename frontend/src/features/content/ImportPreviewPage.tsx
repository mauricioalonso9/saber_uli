import { useQuery } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ImportAction, ImportDetail } from "@/api/content/model";
import { confirmImport, getImport, getImportReport, useGetImport } from "@/api/content/transfer";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { fieldLabel } from "@/features/content/fields";
import { saveBlob } from "@/shared/lib/download";
import { formatDateTime } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";

const ACTIONS: ImportAction[] = ["create", "update", "unchanged", "error"];
const ROWS_PER_PAGE = 100;

/**
 * Vista previa de una importación (US4; FR-030 a FR-036): conteos, filas filtrables con cada error
 * explicado, reporte descargable y la confirmación, que exige elegir el estado y declarar que los
 * ítems son originales.
 */
export function ImportPreview({
  job: initial,
  onConfirmed,
}: {
  job: ImportDetail;
  onConfirmed?: (job: ImportDetail) => void;
}) {
  const { t } = useTranslation();
  const ids = { filter: useId(), state: useId(), table: useId() };
  const [job, setJob] = useState(initial);
  const [action, setAction] = useState<ImportAction | "">("");
  const [target, setTarget] = useState<"draft" | "in_review" | null>(null);
  const [declared, setDeclared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rows = useQuery({
    queryKey: ["import-rows", job.id, action],
    queryFn: () =>
      getImport(job.id, { ...(action ? { action } : {}), page: 1, page_size: ROWS_PER_PAGE }),
  });
  const shown = rows.data?.rows ?? (action ? [] : job.rows);
  const hasAi = (rows.data?.rows ?? job.rows).some((row) => row.target_state === "in_review");

  async function confirm() {
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      const done = await confirmImport(job.id, {
        target_state: target,
        originality_declared: true,
      });
      setJob(done);
      onConfirmed?.(done);
    } catch (failure) {
      setError(problemText(failure));
    } finally {
      setBusy(false);
    }
  }

  async function report() {
    try {
      saveBlob(await getImportReport(job.id), `reporte-importacion-${job.id}.xlsx`);
    } catch (failure) {
      setError(problemText(failure));
    }
  }

  const result = job.result;
  return (
    <section className="space-y-4">
      <ul aria-label={t("content.import.summary")} className="flex flex-wrap gap-3">
        {ACTIONS.map((name) => (
          <li key={name} className="rounded-md border px-3 py-2">
            {t(`content.import.counts.${name}`, { count: job.counts[name] })}
          </li>
        ))}
      </ul>
      {job.status === "pending" && hasAi ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3">
          {t("content.import.aiNotice")}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor={ids.filter} className="font-medium">
            {t("content.import.show")}
          </label>
          <select
            id={ids.filter}
            className="mt-1 block rounded-md border border-input bg-background px-3 py-2"
            value={action}
            onChange={(event) => setAction(event.target.value as ImportAction | "")}
          >
            <option value="">{t("content.import.all")}</option>
            {ACTIONS.map((name) => (
              <option key={name} value={name}>
                {t(`content.import.actions.${name}`)}
              </option>
            ))}
          </select>
        </div>
        {job.counts.error > 0 ? (
          <Button type="button" variant="outline" onClick={() => void report()}>
            {t("content.import.report")}
          </Button>
        ) : null}
      </div>

      <div
        // Se desplaza en pantallas angostas: debe poder recorrerse con el teclado.
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex={0}
        role="region"
        aria-labelledby={ids.table}
        className="overflow-x-auto"
      >
        <table aria-labelledby={ids.table} className="w-full text-left text-sm">
          <caption id={ids.table} className="sr-only">
            {t("content.import.rows")}
          </caption>
          <thead>
            <tr>
              {(["code", "action", "field", "rule", "message"] as const).map((column) => (
                <th key={column} scope="col" className="border-b p-2">
                  {t(`content.import.columns.${column}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.flatMap((row) =>
              (row.errors?.length ? row.errors : [null]).map((issue, index) => (
                <tr key={`${row.entity}-${row.code}-${index}`} className="border-b">
                  <td className="p-2 font-mono">{row.code}</td>
                  <td className="p-2">{t(`content.import.actions.${row.action}`)}</td>
                  <td className="p-2">{issue ? fieldLabel(issue.field) : ""}</td>
                  <td className="p-2">{issue ? t(`content.rules.${issue.rule}`) : ""}</td>
                  <td className="p-2">{issue?.message ?? ""}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>

      {job.status === "expired" ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3">
          {t("content.import.expired")}
        </p>
      ) : null}

      {job.status === "pending" && job.counts.create + job.counts.update === 0 ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3">
          {t("content.import.nothingValid")}
        </p>
      ) : null}

      {job.status === "pending" && job.counts.create + job.counts.update > 0 ? (
        <form
          className="space-y-3 rounded-md border p-4"
          onSubmit={(event) => {
            event.preventDefault();
            void confirm();
          }}
        >
          <p className="text-sm text-muted-foreground">
            {t("content.import.expires", { date: formatDateTime(job.expires_at) })}
          </p>
          <fieldset>
            <legend id={ids.state} className="font-medium">
              {t("content.import.targetState")}
            </legend>
            {(["draft", "in_review"] as const).map((state) => (
              <label key={state} className="mr-4 inline-flex items-center gap-2">
                <input
                  type="radio"
                  name={ids.state}
                  checked={target === state}
                  onChange={() => setTarget(state)}
                />
                {t(`content.import.states.${state}`)}
              </label>
            ))}
          </fieldset>
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              className="mt-1"
              checked={declared}
              onChange={(event) => setDeclared(event.target.checked)}
            />
            {t("content.import.originality")}
          </label>
          <Button type="submit" disabled={!target || !declared || busy}>
            {t("content.import.confirm")}
          </Button>
        </form>
      ) : null}

      {job.status === "confirmed" && result ? (
        <div role="status" className="rounded-md border border-green-300 bg-green-50 p-3">
          <p>
            {t("content.import.confirmed", {
              created: result.created,
              versioned: result.versioned,
              skipped: result.skipped.length,
            })}
          </p>
          {result.skipped.length ? (
            <p>{t("content.import.skipped", { codes: result.skipped.join(", ") })}</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

/** Página de una importación (`/banco/importaciones/$importId`). */
export function ImportPreviewPage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false });
  const id = params.importId ?? "";
  const query = useGetImport(id, { page_size: ROWS_PER_PAGE }, { query: { enabled: Boolean(id) } });

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">{t("content.pages.importPreview")}</h1>
      <ReauthAlert error={query.error} returnTo={`/banco/importaciones/${id}`} />
      {query.isError && !isReauth(query.error) ? (
        <p role="alert">{problemText(query.error)}</p>
      ) : null}
      {query.data ? (
        <>
          <p className="font-mono">{query.data.source_name}</p>
          <ImportPreview key={query.data.id} job={query.data} />
        </>
      ) : null}
    </section>
  );
}
