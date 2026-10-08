import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AdminListDeletionRequestsStatus } from "@/api/model";
import { useAdminListDeletionRequests } from "@/api/admin";
import { formatDateTime, formatDay } from "@/shared/lib/dates";
import { Label } from "@/shared/ui/label";

import { ReauthAlert, isReauth, problemText } from "./common";

const STATUSES: AdminListDeletionRequestsStatus[] = ["received", "in_progress", "completed"];

/**
 * Solicitudes de supresión (FR-034; escenario 7.4): estado, origen y fecha límite. Muestra solo
 * el identificador de la cuenta: tras la supresión ya no hay nombre ni correo.
 */
export function DeletionRequestsPage() {
  const { t } = useTranslation();
  const statusId = useId();
  const [status, setStatus] = useState<AdminListDeletionRequestsStatus | "">("");
  const list = useAdminListDeletionRequests({
    page: 1,
    page_size: 100,
    ...(status ? { status } : {}),
  });

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("admin.deletions.title")}</h1>
      <ReauthAlert error={list.error} returnTo="/admin/supresiones" />
      <div className="mb-6">
        <Label htmlFor={statusId}>{t("admin.deletions.status")}</Label>
        <select
          id={statusId}
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as AdminListDeletionRequestsStatus | "")
          }
          className="mt-1 block h-11 rounded-md border border-input bg-background px-3"
        >
          <option value="">{t("admin.deletions.all")}</option>
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {t(`admin.deletions.statuses.${value}`)}
            </option>
          ))}
        </select>
      </div>

      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data && list.data.items.length === 0 ? <p>{t("admin.deletions.empty")}</p> : null}
      {list.data && list.data.items.length > 0 ? (
        <>
          <p className="mb-2 text-sm text-muted-foreground">
            {t("admin.deletions.count", { count: list.data.total })}
          </p>
          {/* En el celular la tabla se desplaza: el contenedor recibe el foco del teclado. */}
          <div
            role="region"
            aria-label={t("admin.deletions.table")}
            tabIndex={0}
            className="overflow-x-auto"
          >
            <table aria-label={t("admin.deletions.table")} className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  {["requested", "status", "origin", "due", "completed", "account"].map(
                    (column) => (
                      <th key={column} scope="col" className="py-2 pr-3">
                        {t(`admin.deletions.columns.${column}`)}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {list.data.items.map((request) => (
                  <tr key={request.id} className="border-b align-top">
                    <td className="whitespace-nowrap py-2 pr-3">
                      {formatDateTime(request.requested_at)}
                    </td>
                    <td className="py-2 pr-3">{t(`admin.deletions.statuses.${request.status}`)}</td>
                    <td className="py-2 pr-3">{t(`admin.deletions.origins.${request.origin}`)}</td>
                    <td className="whitespace-nowrap py-2 pr-3">{formatDay(request.due_date)}</td>
                    <td className="whitespace-nowrap py-2 pr-3">
                      {request.completed_at ? formatDateTime(request.completed_at) : "—"}
                    </td>
                    <td className="break-all py-2 font-mono text-xs">{request.user_id}</td>
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
