import { Link } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ImportDetail } from "@/api/content/model";
import { createImport, getImportTemplate, useListImports } from "@/api/content/transfer";
import { problemText } from "@/features/admin/common";
import { ImportPreview } from "@/features/content/ImportPreviewPage";
import { saveBlob } from "@/shared/lib/download";
import { formatDateTime } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";

/**
 * Subir un archivo para importar (US4; FR-028, FR-037). Primero se valida y se muestra la vista
 * previa; nada se guarda hasta confirmar. Ofrece la plantilla y las importaciones recientes.
 */
export function ImportUpload() {
  const { t } = useTranslation();
  const ids = { file: useId(), recent: useId() };
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recent = useListImports({ page_size: 10 });

  async function validate() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setJob(await createImport({ file }));
      void recent.refetch();
    } catch (failure) {
      setJob(null);
      setError(problemText(failure));
    } finally {
      setBusy(false);
    }
  }

  async function template() {
    try {
      saveBlob(await getImportTemplate(), "plantilla-banco-saber-uli.xlsx");
    } catch (failure) {
      setError(problemText(failure));
    }
  }

  return (
    <div className="space-y-6">
      <p>{t("content.import.intro")}</p>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void validate();
        }}
      >
        <div>
          <label htmlFor={ids.file} className="font-medium">
            {t("content.import.file")}
          </label>
          <input
            id={ids.file}
            type="file"
            accept=".json,.xlsx,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="mt-1 block"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>
        <Button type="submit" disabled={!file || busy}>
          {busy ? t("content.import.validating") : t("content.import.validate")}
        </Button>
        <Button type="button" variant="outline" onClick={() => void template()}>
          {t("content.import.template")}
        </Button>
      </form>
      {error ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {error}
        </p>
      ) : null}

      {job ? (
        <ImportPreview key={job.id} job={job} onConfirmed={() => void recent.refetch()} />
      ) : null}

      <section aria-labelledby={ids.recent} className="space-y-2">
        <h2 id={ids.recent} className="text-lg font-semibold">
          {t("content.import.recent")}
        </h2>
        {recent.data?.items.length ? (
          <div
            // Se desplaza en pantallas angostas: debe poder recorrerse con el teclado.
            // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
            tabIndex={0}
            role="region"
            aria-labelledby={ids.recent}
            className="overflow-x-auto"
          >
            <table aria-labelledby={ids.recent} className="w-full text-left text-sm">
              <thead>
                <tr>
                  {(["file", "status", "date", "author"] as const).map((column) => (
                    <th key={column} scope="col" className="border-b p-2">
                      {t(`content.import.columns.${column}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recent.data.items.map((item) => (
                  <tr key={item.id} className="border-b">
                    <td className="p-2">
                      <Link to="/banco/importaciones/$importId" params={{ importId: item.id }}>
                        {item.source_name}
                      </Link>
                    </td>
                    <td className="p-2">{t(`content.import.statuses.${item.status}`)}</td>
                    <td className="p-2">{formatDateTime(item.created_at)}</td>
                    <td className="p-2">{item.created_by.display_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>{t("content.import.noRecent")}</p>
        )}
      </section>
    </div>
  );
}

/** Página de importación (`/banco/importar`). */
export function ImportPage() {
  const { t } = useTranslation();
  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">{t("content.pages.import")}</h1>
      <ImportUpload />
    </section>
  );
}
