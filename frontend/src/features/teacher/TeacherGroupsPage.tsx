import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { GroupSummary } from "@/api/model";
import { useListMyGroupStudents, useListMyTeachingGroups } from "@/api/teacher";
import { ReauthAlert, isReauth, problemText } from "@/features/admin/common";
import { Button } from "@/shared/ui/button";

function Students({ group }: { group: GroupSummary }) {
  const { t } = useTranslation();
  const students = useListMyGroupStudents(group.id, { page: 1, page_size: 100 });
  const label = t("teacher.studentsOf", { name: group.name });
  if (students.isPending) return <p role="status">{t("admin.loading")}</p>;
  if (students.isError) return <p role="alert">{problemText(students.error)}</p>;
  return (
    <ul aria-label={label} className="mt-3 list-disc pl-6">
      {students.data.items.map((student) => (
        <li key={student.user_id}>{student.display_name}</li>
      ))}
    </ul>
  );
}

/**
 * Mis grupos (FR-027): los grupos donde la persona es docente y, de sus estudiantes, solo el
 * nombre; el correo nunca llega a esta vista.
 */
export function TeacherGroupsPage() {
  const { t } = useTranslation();
  const groups = useListMyTeachingGroups();
  const [selected, setSelected] = useState<GroupSummary | null>(null);
  const title = useId();

  return (
    <section>
      <h1 id={title} className="mb-4 text-2xl font-bold">
        {t("teacher.title")}
      </h1>
      <ReauthAlert error={groups.error} returnTo="/grupos" />
      {groups.isPending ? <p role="status">{t("admin.loading")}</p> : null}
      {groups.isError && !isReauth(groups.error) ? (
        <p role="alert">{problemText(groups.error)}</p>
      ) : null}
      {groups.data && groups.data.length === 0 ? <p>{t("teacher.empty")}</p> : null}
      {groups.data && groups.data.length > 0 ? (
        <ul className="mb-6 flex flex-col gap-2">
          {groups.data.map((group) => (
            <li key={group.id}>
              <Button
                type="button"
                variant={selected?.id === group.id ? "default" : "outline"}
                aria-pressed={selected?.id === group.id}
                className="h-11"
                onClick={() => setSelected(group)}
              >
                {t("teacher.groupButton", { name: group.name, count: group.member_count })}
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
      {selected ? (
        <section aria-labelledby={`${title}-group`}>
          <h2 id={`${title}-group`} className="text-lg font-semibold">
            {selected.name}
          </h2>
          <Students group={selected} />
        </section>
      ) : null}
    </section>
  );
}
