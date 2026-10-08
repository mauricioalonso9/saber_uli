import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AdminListAuditEventsParams } from "@/api/model";
import { useAdminListAuditEvents } from "@/api/admin";
import { formatDateTime } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

import { ReauthAlert, isReauth, problemText } from "./common";

/** Consulta de auditoría (FR-035): solo lectura, del evento más reciente al más antiguo. */
export function AuditPage() {
  const { t } = useTranslation();
  const ids = { action: useId(), from: useId(), to: useId() };
  const [form, setForm] = useState({ action: "", from: "", to: "" });
  const [filters, setFilters] = useState<AdminListAuditEventsParams>({ page: 1, page_size: 100 });
  const list = useAdminListAuditEvents(filters);

  function apply() {
    const next: AdminListAuditEventsParams = { page: 1, page_size: 100 };
    if (form.action.trim()) next.action = form.action.trim();
    // Días completos en hora de Colombia.
    if (form.from) next.from = `${form.from}T00:00:00-05:00`;
    if (form.to) next.to = `${form.to}T23:59:59-05:00`;
    setFilters(next);
  }

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("admin.audit.title")}</h1>
      <ReauthAlert error={list.error} returnTo="/admin/auditoria" />
      <form
        className="mb-6 flex flex-wrap items-end gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          apply();
        }}
      >
        <div>
          <Label htmlFor={ids.action}>{t("admin.audit.action")}</Label>
          <Input
            id={ids.action}
            className="h-11"
            maxLength={64}
            placeholder="user.disabled"
            value={form.action}
            onChange={(e) => setForm((f) => ({ ...f, action: e.target.value }))}
          />
        </div>
        <div>
          <Label htmlFor={ids.from}>{t("admin.audit.from")}</Label>
          <Input
            id={ids.from}
            type="date"
            className="h-11"
            value={form.from}
            onChange={(e) => setForm((f) => ({ ...f, from: e.target.value }))}
          />
        </div>
        <div>
          <Label htmlFor={ids.to}>{t("admin.audit.to")}</Label>
          <Input
            id={ids.to}
            type="date"
            className="h-11"
            value={form.to}
            onChange={(e) => setForm((f) => ({ ...f, to: e.target.value }))}
          />
        </div>
        <Button type="submit" variant="outline" className="h-11">
          {t("admin.audit.filter")}
        </Button>
      </form>

      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data ? (
        <>
          <p className="mb-2 text-sm text-muted-foreground">
            {t("admin.audit.count", { count: list.data.total })}
          </p>
          <div className="overflow-x-auto">
            <table aria-label={t("admin.audit.table")} className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  {["when", "action", "actor", "target", "details"].map((column) => (
                    <th key={column} scope="col" className="py-2 pr-3">
                      {t(`admin.audit.columns.${column}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.data.items.map((event) => (
                  <tr key={event.id} className="border-b align-top">
                    <td className="whitespace-nowrap py-2 pr-3">
                      {formatDateTime(event.occurred_at)}
                    </td>
                    <td className="py-2 pr-3 font-mono">{event.action}</td>
                    <td className="break-all py-2 pr-3 font-mono text-xs">
                      {event.actor_id ?? t("admin.audit.system")}
                    </td>
                    <td className="py-2 pr-3">{event.target_type}</td>
                    <td className="break-all py-2 font-mono text-xs">
                      {JSON.stringify(event.details ?? {})}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
