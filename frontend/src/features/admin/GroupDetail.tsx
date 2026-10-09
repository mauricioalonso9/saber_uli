import { useQueryClient } from "@tanstack/react-query";
import { getRouteApi } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Role } from "@/api/model";
import {
  getAdminGetGroupQueryKey,
  getAdminListGroupMembersQueryKey,
  useAdminAddGroupMembers,
  useAdminAddGroupTeachers,
  useAdminGetGroup,
  useAdminListGroupMembers,
  useAdminListUsers,
  useAdminRemoveGroupMember,
  useAdminRemoveGroupTeacher,
  useAdminUpdateGroup,
} from "@/api/admin";
import { Button } from "@/shared/ui/button";
import { Label } from "@/shared/ui/label";
import { refreshQueries } from "@/shared/api/refresh";

import { Feedback, ReauthAlert, problemText } from "./common";

const route = getRouteApi("/admin/grupos/$groupId");

interface Person {
  id: string;
  name: string;
  email?: string | null;
}

/** Busca personas con un rol y ofrece agregarlas (estudiantes o docentes del grupo). */
function PeoplePicker({
  accountRole,
  label,
  onAdd,
}: {
  accountRole: Role;
  label: string;
  onAdd: (person: Person) => void;
}) {
  const { t } = useTranslation();
  const id = useId();
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const results = useAdminListUsers(
    { q, role: accountRole, status: "active", page: 1, page_size: 20 },
    { query: { enabled: q.length > 0 } },
  );

  return (
    <div className="mt-4">
      <form
        role="search"
        className="flex items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setQ(search.trim());
        }}
      >
        <div>
          <Label htmlFor={id}>{label}</Label>
          <input
            id={id}
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
      {results.data ? (
        <ul className="mt-2 space-y-1">
          {results.data.items.map((account) => {
            const name = account.display_name ?? account.email ?? "";
            return (
              <li key={account.id} className="flex items-center justify-between gap-2">
                <span>
                  {name} <span className="text-sm text-muted-foreground">{account.email}</span>
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  aria-label={t("admin.groups.addPerson", { name })}
                  onClick={() => onAdd({ id: account.id, name, email: account.email })}
                >
                  {t("admin.groups.add")}
                </Button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

/** Detalle de un grupo (FR-027): estudiantes, docentes y archivado. */
export function GroupDetail() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { groupId } = route.useParams();
  const group = useAdminGetGroup(groupId);
  const members = useAdminListGroupMembers(groupId, { page: 1, page_size: 100 });
  const addMembers = useAdminAddGroupMembers();
  const removeMember = useAdminRemoveGroupMember();
  const addTeachers = useAdminAddGroupTeachers();
  const removeTeacher = useAdminRemoveGroupTeacher();
  const update = useAdminUpdateGroup();
  const ids = { members: useId(), teachers: useId() };
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setMessage(null);
    setError(null);
    try {
      await action();
    } catch (problem) {
      setError(problemText(problem));
      return;
    }
    setMessage(success);
    void refreshQueries(queryClient, getAdminGetGroupQueryKey(groupId));
    void refreshQueries(queryClient, getAdminListGroupMembersQueryKey(groupId));
  }

  if (group.isError) {
    return (
      <section>
        <ReauthAlert error={group.error} returnTo={`/admin/grupos/${groupId}`} />
        <p role="alert">{problemText(group.error)}</p>
      </section>
    );
  }
  if (!group.data) return <p role="status">{t("admin.loading")}</p>;
  const data = group.data;
  const archived = Boolean(data.archived_at);

  return (
    <section>
      <h1 className="mb-1 text-2xl font-bold">{data.name}</h1>
      <p className="mb-4 text-sm text-muted-foreground">
        {[data.cohort_label, archived ? t("admin.groups.archived") : null]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <Feedback message={message} error={error} />
      <Button
        type="button"
        variant="outline"
        className="mb-6"
        onClick={() =>
          void run(
            () => update.mutateAsync({ groupId, data: { archived: !archived } }),
            t(archived ? "admin.groups.unarchived" : "admin.groups.archivedDone"),
          )
        }
      >
        {t(archived ? "admin.groups.unarchive" : "admin.groups.archive")}
      </Button>

      <section aria-labelledby={ids.members} className="mb-8 rounded-md border p-4">
        <h2 id={ids.members} className="mb-2 text-lg font-semibold">
          {t("admin.groups.students")}
        </h2>
        <ul className="space-y-1">
          {members.data?.items.map((member) => {
            const name = member.display_name ?? member.email ?? "";
            return (
              <li key={member.user_id} className="flex items-center justify-between gap-2">
                <span>
                  {name} <span className="text-sm text-muted-foreground">{member.email}</span>
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  aria-label={t("admin.groups.removePerson", { name })}
                  onClick={() =>
                    void run(
                      () => removeMember.mutateAsync({ groupId, userId: member.user_id }),
                      t("admin.groups.removed", { name }),
                    )
                  }
                >
                  {t("admin.groups.remove")}
                </Button>
              </li>
            );
          })}
        </ul>
        <PeoplePicker
          accountRole="student"
          label={t("admin.groups.searchStudents")}
          onAdd={(person) =>
            void run(
              () => addMembers.mutateAsync({ groupId, data: { user_ids: [person.id] } }),
              t("admin.groups.added", { name: person.name }),
            )
          }
        />
      </section>

      <section aria-labelledby={ids.teachers} className="rounded-md border p-4">
        <h2 id={ids.teachers} className="mb-2 text-lg font-semibold">
          {t("admin.groups.teachers")}
        </h2>
        <ul className="space-y-1">
          {data.teachers.map((teacher) => (
            <li key={teacher.id} className="flex items-center justify-between gap-2">
              <span>{teacher.display_name}</span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                aria-label={t("admin.groups.removePerson", { name: teacher.display_name })}
                onClick={() =>
                  void run(
                    () => removeTeacher.mutateAsync({ groupId, userId: teacher.id }),
                    t("admin.groups.removed", { name: teacher.display_name }),
                  )
                }
              >
                {t("admin.groups.remove")}
              </Button>
            </li>
          ))}
        </ul>
        <PeoplePicker
          accountRole="teacher"
          label={t("admin.groups.searchTeachers")}
          onAdd={(person) =>
            void run(
              () => addTeachers.mutateAsync({ groupId, data: { user_ids: [person.id] } }),
              t("admin.groups.added", { name: person.name }),
            )
          }
        />
      </section>
    </section>
  );
}
