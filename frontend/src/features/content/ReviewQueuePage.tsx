import { Link } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useListItems } from "@/api/content/items";
import type { ModuleCodeValue } from "@/api/content/model";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { Label } from "@/shared/ui/label";
import { ScrollRegion } from "@/shared/ui/ScrollRegion";

export const MODULES: ModuleCodeValue[] = ["LC", "RC", "CC", "ING", "CE"];

/**
 * Cola de revisión (US2; FR-013): los ítems En revisión que quien consulta puede aprobar. Los de
 * origen IA se marcan (FR-019) y se avisa cuando ningún otro administrador puede aprobar uno
 * porque todos lo modificaron (FR-012).
 */
export function ReviewQueuePage() {
  const { t } = useTranslation();
  const moduleId = useId();
  const [module, setModule] = useState<ModuleCodeValue | "">("");
  const list = useListItems({
    awaiting_my_review: true,
    page: 1,
    page_size: 50,
    ...(module ? { module } : {}),
  });

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("content.pages.review")}</h1>
      <ReauthAlert error={list.error} returnTo="/banco/revision" />
      <div className="mb-6">
        <Label htmlFor={moduleId}>{t("content.fields.module")}</Label>
        <select
          id={moduleId}
          value={module}
          onChange={(event) => setModule(event.target.value as ModuleCodeValue | "")}
          className="mt-1 block h-11 rounded-md border border-input bg-background px-3"
        >
          <option value="">{t("content.filters.all")}</option>
          {MODULES.map((code) => (
            <option key={code} value={code}>
              {t(`content.modules.${code}`)}
            </option>
          ))}
        </select>
      </div>
      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data && list.data.items.length === 0 ? <p>{t("content.review.empty")}</p> : null}
      {list.data && list.data.items.length > 0 ? (
        <ScrollRegion label={t("content.review.table")}>
          <table aria-label={t("content.review.table")} className="w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                {["code", "module", "stem", "origin", "note"].map((column) => (
                  <th key={column} scope="col" className="py-2 pr-3">
                    {t(`content.columns.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((entry) => (
                <tr key={entry.code} className="border-b align-top">
                  <td className="whitespace-nowrap py-2 pr-3">
                    <Link
                      to="/banco/items/$code"
                      params={{ code: entry.code }}
                      className="underline"
                    >
                      {entry.code}
                    </Link>
                  </td>
                  <td className="py-2 pr-3">{t(`content.modules.${entry.module}`)}</td>
                  <td className="py-2 pr-3">{entry.stem_excerpt}</td>
                  <td className="py-2 pr-3">
                    {entry.origin === "ai" ? (
                      <span className="rounded bg-violet-100 px-2 py-0.5 text-violet-900">
                        {t("content.origins.ai")}
                      </span>
                    ) : (
                      t(`content.origins.${entry.origin}`)
                    )}
                  </td>
                  <td className="py-2 pr-3">
                    {entry.needs_another_reviewer ? t("content.review.needsAnother") : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollRegion>
      ) : null}
    </section>
  );
}
