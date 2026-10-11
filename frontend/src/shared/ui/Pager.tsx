import { useTranslation } from "react-i18next";

import { Button } from "@/shared/ui/button";

/** Paginación de un listado: "Página X de Y · N ítems" con Anterior y Siguiente. */
export function Pager({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const { t } = useTranslation();
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav aria-label={t("pager.label")} className="flex flex-wrap items-center gap-3">
      <Button
        type="button"
        variant="outline"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        {t("pager.previous")}
      </Button>
      <span aria-live="polite">{t("pager.status", { page, pages, count: total })}</span>
      <Button
        type="button"
        variant="outline"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        {t("pager.next")}
      </Button>
    </nav>
  );
}
