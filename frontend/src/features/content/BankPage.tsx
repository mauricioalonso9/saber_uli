import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { ItemSummary, ListItemsParams } from "@/api/content/model";
import { useListItems } from "@/api/content/items";
import { useListContentModules } from "@/api/content/taxonomy";
import type { BankSearch } from "@/app/router";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { Pager } from "@/shared/ui/Pager";
import { ScrollRegion } from "@/shared/ui/ScrollRegion";
import { SearchBox } from "@/shared/ui/SearchBox";

const PAGE_SIZE = 25;
const SELECT = "mt-1 block h-11 w-full rounded-md border border-input bg-background px-3";
const FILTERS = {
  state: ["draft", "in_review", "published", "retired"],
  origin: ["seed", "teacher", "ai"],
  difficulty: ["low", "medium", "high"],
  signal: ["too_easy", "too_hard", "negative_discrimination", "distractor_beats_key"],
} as const;

function useStateText() {
  const { t } = useTranslation();
  return (item: ItemSummary): string => {
    if (item.retired) return t("content.states.retired");
    const parts = [];
    if (item.published_version != null) {
      parts.push(`${t("content.states.published")} (v${item.published_version})`);
    }
    if (item.open_version) {
      parts.push(
        `${t(`content.states.${item.open_version.state}`)} (v${item.open_version.number})`,
      );
    }
    return parts.join(" · ");
  };
}

/**
 * Lista del banco (fase 13; FR-039, FR-043, SC-009): búsqueda, filtros y página en la URL, para
 * que la cobertura enlace a una categoría y el botón Atrás conserve lo elegido.
 */
export function BankPage() {
  const { t } = useTranslation();
  const id = useId();
  const search: BankSearch = useSearch({ strict: false });
  const navigate = useNavigate();
  const stateText = useStateText();
  const modules = useListContentModules().data?.items ?? [];
  const page = search.page ?? 1;
  const params: ListItemsParams = { page, page_size: PAGE_SIZE };
  for (const name of [
    "q",
    "module",
    "state",
    "origin",
    "difficulty",
    "taxonomy_node",
    "signal",
  ] as const) {
    if (search[name]) Object.assign(params, { [name]: search[name] });
  }
  const list = useListItems(params);
  const nodes = modules.find((m) => m.code === search.module)?.nodes ?? [];

  function update(change: Partial<BankSearch>) {
    const next: BankSearch = { ...search, ...change };
    // Cambiar un filtro vuelve a la primera página; la categoría depende del módulo.
    if (!("page" in change)) delete next.page;
    if ("module" in change) delete next.taxonomy_node;
    for (const key of Object.keys(next) as (keyof BankSearch)[]) {
      if (next[key] === undefined || next[key] === "") delete next[key];
    }
    void navigate({ to: "/banco", search: next, replace: true });
  }

  function filter(
    name: keyof BankSearch,
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
          value={String(search[name] ?? "")}
          onChange={(event) => update({ [name]: event.target.value || undefined })}
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

  const data = list.data;
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("content.pages.bank")}</h1>
        <Link to="/banco/items/nuevo" className="underline">
          {t("content.bank.newItem")}
        </Link>
      </div>
      <SearchBox
        key={search.q ?? ""}
        value={search.q ?? ""}
        hint={t("content.bank.searchHint")}
        onSearch={(q) => update({ q: q || undefined })}
      />
      <div className="grid gap-4 sm:grid-cols-3">
        {filter(
          "module",
          t("content.fields.module"),
          modules.map((m) => ({ value: m.code, label: t(`content.modules.${m.code}`) })),
        )}
        {search.module
          ? filter(
              "taxonomy_node",
              t("content.bank.category"),
              nodes.map((n) => ({ value: n.id, label: `${n.code} · ${n.name}` })),
            )
          : null}
        {filter(
          "state",
          t("content.bank.state"),
          FILTERS.state.map((v) => ({ value: v, label: t(`content.states.${v}`) })),
        )}
        {filter(
          "origin",
          t("content.bank.origin"),
          FILTERS.origin.map((v) => ({ value: v, label: t(`content.origins.${v}`) })),
        )}
        {filter(
          "difficulty",
          t("content.editor.difficulty"),
          FILTERS.difficulty.map((v) => ({
            value: v,
            label: t(`content.editor.difficulties.${v}`),
          })),
        )}
        {filter(
          "signal",
          t("content.bank.signal"),
          FILTERS.signal.map((v) => ({ value: v, label: t(`content.bank.signals.${v}`) })),
        )}
      </div>

      <ReauthAlert error={list.error} returnTo="/banco" />
      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {data && data.items.length === 0 ? <p>{t("content.bank.empty")}</p> : null}
      {data && data.items.length > 0 ? (
        <>
          <ScrollRegion label={t("content.bank.table")}>
            <table aria-label={t("content.bank.table")} className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  {(
                    ["code", "module", "state", "origin", "difficulty", "stem", "signals"] as const
                  ).map((column) => (
                    <th key={column} scope="col" className="py-2 pr-3">
                      {t(`content.bank.columns.${column}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.code} className="border-b align-top">
                    <td className="whitespace-nowrap py-2 pr-3">
                      <Link
                        to="/banco/items/$code"
                        params={{ code: item.code }}
                        className="font-mono underline"
                      >
                        {item.code}
                      </Link>
                    </td>
                    <td className="py-2 pr-3">{t(`content.modules.${item.module}`)}</td>
                    <td className="py-2 pr-3">{stateText(item)}</td>
                    <td className="py-2 pr-3">{t(`content.origins.${item.origin}`)}</td>
                    <td className="py-2 pr-3">
                      {t(`content.editor.difficulties.${item.difficulty}`)}
                    </td>
                    <td className="py-2 pr-3">{item.stem_excerpt}</td>
                    <td className="py-2 pr-3">
                      {(item.signals ?? []).map((s) => t(`content.bank.signals.${s}`)).join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollRegion>
          <Pager
            page={page}
            pageSize={PAGE_SIZE}
            total={data.meta.total}
            onChange={(next) => update({ page: next })}
          />
        </>
      ) : null}
    </section>
  );
}
