import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { GroupInput } from "@/api/model";
import { getAdminListGroupsQueryKey, useAdminCreateGroup, useAdminListGroups } from "@/api/admin";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { ScrollRegion } from "@/shared/ui/ScrollRegion";
import { refreshQueries } from "@/shared/api/refresh";

import { Feedback, ReauthAlert, isReauth, problemText } from "./common";

/** Grupos o cohortes (FR-027): listado y creación; el detalle está en `/admin/grupos/<id>`. */
export function GroupsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const list = useAdminListGroups({ page: 1, page_size: 100 });
  const create = useAdminCreateGroup();
  const ids = { title: useId(), name: useId(), cohort: useId(), description: useId() };
  const [name, setName] = useState("");
  const [cohort, setCohort] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setMessage(null);
    setError(null);
    const trimmed = name.trim();
    if (trimmed.length < 2 || trimmed.length > 120) {
      setError(t("admin.groups.errors.name"));
      return;
    }
    const data: GroupInput = { name: trimmed };
    if (cohort.trim()) data.cohort_label = cohort.trim();
    if (description.trim()) data.description = description.trim();
    try {
      await create.mutateAsync({ data });
    } catch (problem) {
      setError(problemText(problem));
      return;
    }
    setMessage(t("admin.groups.created", { name: trimmed }));
    setName("");
    setCohort("");
    setDescription("");
    void refreshQueries(queryClient, getAdminListGroupsQueryKey());
  }

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("admin.groups.title")}</h1>
      <ReauthAlert error={list.error} returnTo="/admin/grupos" />
      <Feedback message={message} error={error} />

      <form
        aria-labelledby={ids.title}
        noValidate
        className="mb-8 space-y-3 rounded-md border p-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <h2 id={ids.title} className="text-lg font-semibold">
          {t("admin.groups.createTitle")}
        </h2>
        <div>
          <Label htmlFor={ids.name}>{t("admin.groups.name")}</Label>
          <Input
            id={ids.name}
            className="h-11"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor={ids.cohort}>{t("admin.groups.cohort")}</Label>
          <Input
            id={ids.cohort}
            className="h-11"
            maxLength={20}
            value={cohort}
            onChange={(e) => setCohort(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor={ids.description}>{t("admin.groups.description")}</Label>
          <Input
            id={ids.description}
            className="h-11"
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <Button type="submit" className="h-11" disabled={create.isPending}>
          {t("admin.groups.create")}
        </Button>
      </form>

      {list.isPending ? <p role="status">{t("admin.loading")}</p> : null}
      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data ? (
        <ScrollRegion label={t("admin.groups.table")}>
          <table aria-label={t("admin.groups.table")} className="w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                {["name", "cohort", "members", "teachers", "state", "actions"].map((column) => (
                  <th key={column} scope="col" className="py-2 pr-3">
                    {t(`admin.groups.columns.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((group) => (
                <tr key={group.id} className="border-b align-top">
                  <td className="py-2 pr-3">{group.name}</td>
                  <td className="py-2 pr-3">{group.cohort_label ?? ""}</td>
                  <td className="py-2 pr-3">{group.member_count}</td>
                  <td className="py-2 pr-3">
                    {group.teachers.map((teacher) => teacher.display_name).join(", ")}
                  </td>
                  <td className="py-2 pr-3">
                    {group.archived_at ? t("admin.groups.archived") : t("admin.groups.active")}
                  </td>
                  <td className="py-2">
                    <Link
                      to="/admin/grupos/$groupId"
                      params={{ groupId: group.id }}
                      className="underline"
                      aria-label={t("admin.groups.manageOf", { name: group.name })}
                    >
                      {t("admin.groups.manage")}
                    </Link>
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
