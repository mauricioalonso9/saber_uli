import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ExportItemsParams } from "@/api/content/model";
import { getExportItemsUrl } from "@/api/content/transfer";
import { useListContentModules } from "@/api/content/taxonomy";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { downloadFile } from "@/shared/api/http";
import { saveBlob } from "@/shared/lib/download";
import { Button } from "@/shared/ui/button";

type Format = ExportItemsParams["format"];
type Version = NonNullable<ExportItemsParams["version"]>;

const STATES = ["draft", "in_review", "published", "retired"] as const;
const ORIGINS = ["seed", "teacher", "ai"] as const;
const DIFFICULTIES = ["low", "medium", "high"] as const;
const SELECT = "mt-1 block w-full rounded-md border border-input bg-background px-3 py-2";

interface Done {
  filename: string;
  skipped: number;
}

/**
 * Exportación del banco (US6; FR-038): el banco o un filtro, en JSON o en la plantilla XLSX, con
 * la versión publicada o la última de cada ítem. Avisa cuántos ítems no caben en la plantilla.
 */
export function ExportPage() {
  const { t } = useTranslation();
  const id = useId();
  const modules = useListContentModules().data?.items ?? [];
  const [format, setFormat] = useState<Format>("json");
  const [version, setVersion] = useState<Version>("published");
  const [filters, setFilters] = useState<Omit<ExportItemsParams, "format" | "version">>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const [error, setError] = useState<unknown>(null);
  const nodes = modules.find((module) => module.code === filters.module)?.nodes ?? [];

  function choose<K extends keyof typeof filters>(name: K, value: string) {
    setFilters((current) => {
      const next = { ...current, [name]: value || undefined };
      // La categoría depende del módulo.
      if (name === "module") delete next.taxonomy_node;
      return next;
    });
  }

  async function exportBank() {
    setBusy(true);
    setDone(null);
    setError(null);
    try {
      const params: ExportItemsParams = { format, version };
      for (const [name, value] of Object.entries(filters)) {
        if (value) Object.assign(params, { [name]: value });
      }
      const file = await downloadFile(getExportItemsUrl(params));
      const filename = file.filename ?? `banco-saber-uli.${format}`;
      saveBlob(file.blob, filename);
      setDone({ filename, skipped: Number(file.headers.get("X-Skipped-Items") ?? 0) });
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  function filter<K extends keyof typeof filters>(
    name: K,
    label: string,
    options: readonly { value: string; label: string }[],
  ) {
    return (
      <div>
        <label htmlFor={`${id}-${name}`} className="font-medium">
          {label}
        </label>
        <select
          id={`${id}-${name}`}
          className={SELECT}
          value={filters[name] ?? ""}
          onChange={(event) => choose(name, event.target.value)}
        >
          <option value="">{t("content.filters.all")}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">{t("content.pages.export")}</h1>
      <p>{t("content.export.intro")}</p>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void exportBank();
        }}
      >
        <fieldset>
          <legend className="font-medium">{t("content.export.format")}</legend>
          {(["json", "xlsx"] as const).map((value) => (
            <label key={value} className="mr-4 inline-flex items-center gap-2">
              <input
                type="radio"
                name={`${id}-format`}
                checked={format === value}
                onChange={() => setFormat(value)}
              />
              {t(`content.export.formats.${value}`)}
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend className="font-medium">{t("content.export.version")}</legend>
          {(["published", "latest"] as const).map((value) => (
            <label key={value} className="mr-4 inline-flex items-center gap-2">
              <input
                type="radio"
                name={`${id}-version`}
                checked={version === value}
                onChange={() => setVersion(value)}
              />
              {t(`content.export.versions.${value}`)}
            </label>
          ))}
        </fieldset>
        <div className="grid gap-4 sm:grid-cols-2">
          {filter(
            "module",
            t("content.fields.module"),
            modules.map((module) => ({
              value: module.code,
              label: t(`content.modules.${module.code}`),
            })),
          )}
          {filters.module
            ? filter(
                "taxonomy_node",
                t("content.export.category"),
                nodes.map((node) => ({ value: node.id, label: `${node.code} · ${node.name}` })),
              )
            : null}
          {filter(
            "state",
            t("content.export.state"),
            STATES.map((value) => ({ value, label: t(`content.states.${value}`) })),
          )}
          {filter(
            "origin",
            t("content.export.origin"),
            ORIGINS.map((value) => ({ value, label: t(`content.origins.${value}`) })),
          )}
          {filter(
            "difficulty",
            t("content.editor.difficulty"),
            DIFFICULTIES.map((value) => ({
              value,
              label: t(`content.editor.difficulties.${value}`),
            })),
          )}
        </div>
        <Button type="submit" disabled={busy}>
          {busy ? t("content.export.exporting") : t("content.export.submit")}
        </Button>
      </form>

      <ReauthAlert error={error} returnTo="/banco/exportar" />
      {error && !isReauth(error) ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {problemText(error)}
        </p>
      ) : null}
      {done ? (
        <div role="status" className="rounded-md border border-green-300 bg-green-50 p-3">
          <p>{t("content.export.done", { filename: done.filename })}</p>
          {done.skipped > 0 ? <p>{t("content.export.skipped", { count: done.skipped })}</p> : null}
        </div>
      ) : null}
    </section>
  );
}
