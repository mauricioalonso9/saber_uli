import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AdminListUsersParams, AdminUser, Role } from "@/api/model";
import {
  getAdminListUsersQueryKey,
  useAdminListUsers,
  useAdminUpdateUserStatus,
} from "@/api/admin";
import { Button } from "@/shared/ui/button";
import { Label } from "@/shared/ui/label";

import { UserRolesEditor } from "./UserRolesEditor";
import {
  Feedback,
  ROLE_ORDER,
  ReauthAlert,
  isReauth,
  problemText,
  useRoleLabel,
  useStatusLabel,
} from "./common";

/**
 * Cuentas (FR-023 a FR-026, FR-029): buscar, definir roles y programas del director, y
 * desactivar o reactivar. Desactivar cierra las sesiones de la persona de inmediato.
 */
export function UsersPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const roleLabel = useRoleLabel();
  const statusLabel = useStatusLabel();
  const ids = { search: useId(), role: useId(), confirm: useId() };
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState<Role | "">("");
  const [editing, setEditing] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<AdminUser | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const setStatus = useAdminUpdateUserStatus();

  const params: AdminListUsersParams = { page: 1, page_size: 50 };
  if (q) params.q = q;
  if (role) params.role = role;
  const list = useAdminListUsers(params);

  useEffect(() => {
    if (confirming) confirmButton.current?.focus();
  }, [confirming]);

  const refresh = () =>
    void queryClient.invalidateQueries({ queryKey: getAdminListUsersQueryKey() });
  const done = (text: string) => {
    setError(null);
    setMessage(text);
    refresh();
  };
  const failed = (text: string) => {
    setMessage(null);
    setError(text);
  };
  const nameOf = (account: AdminUser) => account.display_name ?? account.email ?? "";

  async function changeStatus(account: AdminUser, status: "active" | "disabled") {
    try {
      await setStatus.mutateAsync({ userId: account.id, data: { status } });
    } catch (problem) {
      failed(problemText(problem));
      return;
    }
    setConfirming(null);
    done(
      t(status === "disabled" ? "admin.users.disabled" : "admin.users.reactivated", {
        name: nameOf(account),
      }),
    );
  }

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("admin.users.title")}</h1>
      <ReauthAlert error={list.error} returnTo="/admin/usuarios" />
      <Feedback message={message} error={error} />

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
            <Label htmlFor={ids.search}>{t("admin.users.search")}</Label>
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
          <Label htmlFor={ids.role}>{t("admin.users.role")}</Label>
          <select
            id={ids.role}
            value={role}
            onChange={(event) => setRole(event.target.value as Role | "")}
            className="mt-1 h-11 rounded-md border border-input bg-background px-3"
          >
            <option value="">{t("invitations.filters.all")}</option>
            {ROLE_ORDER.map((value) => (
              <option key={value} value={value}>
                {roleLabel(value)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {list.isPending ? <p role="status">{t("admin.loading")}</p> : null}
      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data ? (
        <div className="overflow-x-auto">
          <table aria-label={t("admin.users.table")} className="w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                {["name", "email", "kind", "roles", "status", "actions"].map((column) => (
                  <th key={column} scope="col" className="py-2 pr-3">
                    {t(`admin.users.columns.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((account) => (
                <tr key={account.id} className="border-b align-top">
                  <td className="py-2 pr-3">{account.display_name ?? "—"}</td>
                  <td className="break-all py-2 pr-3">{account.email ?? "—"}</td>
                  <td className="py-2 pr-3">{t(`admin.kinds.${account.kind}`)}</td>
                  <td className="py-2 pr-3">
                    {ROLE_ORDER.filter((r) => account.roles.includes(r))
                      .map(roleLabel)
                      .join(", ")}
                  </td>
                  <td className="py-2 pr-3">{statusLabel(account.status)}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {account.status !== "deleted" ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          aria-expanded={editing === account.id}
                          aria-label={t("admin.users.editRolesOf", { name: nameOf(account) })}
                          onClick={() => setEditing(editing === account.id ? null : account.id)}
                        >
                          {t("admin.users.editRoles")}
                        </Button>
                      ) : null}
                      {account.status === "disabled" ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          aria-label={t("admin.users.reactivateOf", { name: nameOf(account) })}
                          onClick={() => void changeStatus(account, "active")}
                        >
                          {t("admin.users.reactivate")}
                        </Button>
                      ) : account.status === "active" ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          aria-label={t("admin.users.disableOf", { name: nameOf(account) })}
                          onClick={() => setConfirming(account)}
                        >
                          {t("admin.users.disable")}
                        </Button>
                      ) : null}
                    </div>
                    {editing === account.id ? (
                      <UserRolesEditor
                        account={account}
                        onSaved={(text) => {
                          setEditing(null);
                          done(text);
                        }}
                        onError={failed}
                        onCancel={() => setEditing(null)}
                      />
                    ) : null}
                    {confirming?.id === account.id ? (
                      <div
                        role="alertdialog"
                        aria-labelledby={ids.confirm}
                        className="mt-3 rounded-md border border-destructive p-3"
                      >
                        <p id={ids.confirm} className="mb-2 font-semibold">
                          {t("admin.users.confirmDisable", { name: nameOf(account) })}
                        </p>
                        <p className="mb-3 text-sm">{t("admin.users.confirmDisableBody")}</p>
                        <div className="flex gap-2">
                          <Button
                            ref={confirmButton}
                            type="button"
                            size="sm"
                            variant="destructive"
                            onClick={() => void changeStatus(account, "disabled")}
                          >
                            {t("admin.users.confirmYes")}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setConfirming(null)}
                          >
                            {t("invitations.actions.cancel")}
                          </Button>
                        </div>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
