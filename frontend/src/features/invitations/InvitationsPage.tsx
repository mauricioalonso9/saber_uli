import { useQueryClient } from "@tanstack/react-query";
import { useRouteContext } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { InvitationStatus, ListInvitationsParams } from "@/api/model";
import { getListInvitationsQueryKey, useListInvitations } from "@/api/invitations";
import { startMicrosoftLogin } from "@/features/auth/bootstrap";
import { ApiProblem } from "@/shared/api/http";
import { formatDate } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";
import { Label } from "@/shared/ui/label";

import { BatchUpload } from "./BatchUpload";
import { InvitationActions } from "./InvitationActions";
import { InviteForm, problemText } from "./InviteForm";

const STATUSES: InvitationStatus[] = ["sent", "accepted", "expired", "revoked"];

/**
 * Invitaciones (FR-006 a FR-010; escenarios 5.1 a 5.7). Un docente ve y gestiona solo las que
 * envió (el servidor aplica el alcance); un administrador ve todas y puede quedarse con las suyas.
 * Todas las acciones exigen sesión privilegiada: si venció, se ofrece confirmar la identidad.
 */
export function InvitationsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { session } = useRouteContext({ from: "__root__" });
  const me = session?.kind === "authenticated" ? session.me : null;
  const isAdmin = me?.permissions.includes("invitations:manage_all") ?? false;
  const [status, setStatus] = useState<InvitationStatus | "">("");
  const [mine, setMine] = useState(false);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ids = { status: useId(), mine: useId(), search: useId() };

  const params: ListInvitationsParams = { page: 1, page_size: 100 };
  if (status) params.status = status;
  if (q) params.q = q;
  if (isAdmin && mine && me) params.invited_by = me.id;
  const list = useListInvitations(params);

  const refresh = () =>
    void queryClient.invalidateQueries({ queryKey: getListInvitationsQueryKey() });

  const reauth =
    list.error instanceof ApiProblem && list.error.slug === "reauthentication-required";

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("invitations.title")}</h1>

      {reauth ? (
        <div role="alert" className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-4">
          <p className="mb-3">{(list.error as ApiProblem).message}</p>
          <Button type="button" onClick={() => startMicrosoftLogin("/invitaciones")}>
            {t("invitations.reauth")}
          </Button>
        </div>
      ) : null}

      <InviteForm onCreated={refresh} />
      <BatchUpload onConfirmed={refresh} />

      <h2 className="mb-3 text-lg font-semibold">{t("invitations.listTitle")}</h2>
      {message ? (
        <p role="status" className="mb-3 rounded-md border border-green-300 bg-green-50 p-3">
          {message}
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="mb-3 rounded-md border border-red-300 bg-red-50 p-3 text-red-900"
        >
          {error}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <form
          role="search"
          className="flex items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            setQ(search.trim());
          }}
        >
          <div>
            <Label htmlFor={ids.search}>{t("invitations.filters.search")}</Label>
            <input
              id={ids.search}
              type="search"
              maxLength={254}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="mt-1 h-11 rounded-md border border-input bg-background px-3"
            />
          </div>
          <Button type="submit" variant="outline" className="h-11">
            {t("invitations.filters.searchButton")}
          </Button>
        </form>
        <div>
          <Label htmlFor={ids.status}>{t("invitations.filters.status")}</Label>
          <select
            id={ids.status}
            className="mt-1 h-11 rounded-md border border-input bg-background px-3"
            value={status}
            onChange={(event) => setStatus(event.target.value as InvitationStatus | "")}
          >
            <option value="">{t("invitations.filters.all")}</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {t(`invitations.status.${value}`)}
              </option>
            ))}
          </select>
        </div>
        {isAdmin ? (
          <label htmlFor={ids.mine} className="flex min-h-11 items-center gap-2">
            <input
              id={ids.mine}
              type="checkbox"
              className="size-5"
              checked={mine}
              onChange={(event) => setMine(event.target.checked)}
            />
            {t("invitations.filters.mine")}
          </label>
        ) : null}
      </div>

      {list.isPending ? <p role="status">{t("invitations.loading")}</p> : null}
      {list.isError && !reauth ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data ? (
        <p className="mb-2 text-sm text-muted-foreground">
          {t("invitations.count", { count: list.data.total })}
          {list.data.total > list.data.items.length
            ? ` ${t("invitations.partial", { shown: list.data.items.length })}`
            : ""}
        </p>
      ) : null}
      {list.data ? (
        list.data.items.length === 0 ? (
          <p>{t("invitations.empty")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table aria-label={t("invitations.listTitle")} className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.table.email")}
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.table.name")}
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.table.status")}
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.table.until")}
                  </th>
                  {isAdmin ? (
                    <th scope="col" className="py-2 pr-3">
                      {t("invitations.table.invitedBy")}
                    </th>
                  ) : null}
                  <th scope="col" className="py-2">
                    {t("invitations.table.actions")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.data.items.map((item) => (
                  <tr key={item.id} className="border-b align-top">
                    <td className="break-all py-2 pr-3">
                      {item.email ?? t("invitations.table.noEmail")}
                    </td>
                    <td className="py-2 pr-3">{item.invitee_name ?? ""}</td>
                    <td className="py-2 pr-3">{t(`invitations.status.${item.status}`)}</td>
                    <td className="py-2 pr-3">{formatDate(item.access_expires_at)}</td>
                    {isAdmin ? (
                      <td className="py-2 pr-3">
                        {item.invited_by
                          ? (item.invited_by.display_name ?? t("invitations.table.erased"))
                          : t("invitations.table.system")}
                      </td>
                    ) : null}
                    <td className="py-2">
                      <InvitationActions
                        invitation={item}
                        onDone={(text) => {
                          setError(null);
                          setMessage(text);
                          refresh();
                        }}
                        onError={(text) => {
                          setMessage(null);
                          setError(text);
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : null}
    </section>
  );
}
