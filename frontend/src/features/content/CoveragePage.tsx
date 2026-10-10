import { Link } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModuleCodeValue } from "@/api/content/model";
import { useGetModuleCoverage } from "@/api/content/insights";
import { useListContentModules } from "@/api/content/taxonomy";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { ScrollRegion } from "@/shared/ui/ScrollRegion";

const PERCENT = new Intl.NumberFormat("es-CO", { style: "percent", maximumFractionDigits: 0 });
const COLUMNS = ["category", "published", "inReview", "share", "target", "status"] as const;

/**
 * Cobertura del banco frente a la distribución del examen (US7; FR-039): por categoría, los
 * publicados y en revisión, el porcentaje real y el objetivo, y cuántos faltan. Lo que está bajo
 * el objetivo se dice en texto ("Faltan N"), no solo con color.
 */
export function CoveragePage() {
  const { t } = useTranslation();
  const ids = { module: useId(), caption: useId() };
  const modules = useListContentModules().data?.items ?? [];
  const [module, setModule] = useState<ModuleCodeValue>("LC");
  const query = useGetModuleCoverage(module);
  const coverage = query.data;
  const moduleName = t(`content.modules.${module}`);
  const categories = [...(coverage?.categories ?? [])].sort(
    (a, b) => b.missing - a.missing || a.code.localeCompare(b.code),
  );

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">{t("content.pages.coverage")}</h1>
      <div className="max-w-xs">
        <label htmlFor={ids.module} className="font-medium">
          {t("content.fields.module")}
        </label>
        <select
          id={ids.module}
          className="mt-1 block w-full rounded-md border border-input bg-background px-3 py-2"
          value={module}
          onChange={(event) => setModule(event.target.value as ModuleCodeValue)}
        >
          {(modules.length ? modules.map((m) => m.code) : [module]).map((code) => (
            <option key={code} value={code}>
              {t(`content.modules.${code}`)}
            </option>
          ))}
        </select>
      </div>

      <ReauthAlert error={query.error} returnTo="/banco/cobertura" />
      {query.isError && !isReauth(query.error) ? (
        <p role="alert">{problemText(query.error)}</p>
      ) : null}

      {coverage ? (
        <>
          <p>
            {t("content.coverage.summary", {
              target: coverage.bank_target,
              published: coverage.published_total,
              inReview: coverage.in_review_total,
            })}
          </p>
          {categories.length === 0 ? (
            <p>{t("content.coverage.noWeights")}</p>
          ) : (
            <ScrollRegion label={t("content.coverage.table", { module: moduleName })}>
              <table aria-labelledby={ids.caption} className="w-full text-left text-sm">
                <caption id={ids.caption} className="sr-only">
                  {t("content.coverage.table", { module: moduleName })}
                </caption>
                <thead>
                  <tr>
                    {COLUMNS.map((column) => (
                      <th key={column} scope="col" className="border-b p-2">
                        {t(`content.coverage.columns.${column}`)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {categories.map((category) => (
                    <tr key={category.node_id} className="border-b">
                      <th scope="row" className="p-2 font-normal">
                        <Link
                          to="/banco"
                          search={{ module, taxonomy_node: category.node_id }}
                          className="underline"
                        >
                          <span className="font-mono">{category.code}</span> {category.name}
                        </Link>
                      </th>
                      <td className="p-2">{category.published}</td>
                      <td className="p-2">{category.in_review}</td>
                      <td className="p-2">{PERCENT.format(category.published_share)}</td>
                      <td className="p-2">
                        {category.target_weight == null
                          ? "—"
                          : PERCENT.format(category.target_weight)}
                      </td>
                      <td className="p-2">
                        {category.below_target ? (
                          <span className="font-medium text-amber-800">
                            {t("content.coverage.missing", { count: category.missing })}
                          </span>
                        ) : (
                          <span className="text-green-800">{t("content.coverage.met")}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollRegion>
          )}
        </>
      ) : null}
    </section>
  );
}
