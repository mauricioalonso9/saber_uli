import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AdminUser, Role } from "@/api/model";
import { useAdminListPrograms, useAdminSetUserRoles } from "@/api/admin";
import { Button } from "@/shared/ui/button";

import { ROLE_ORDER, problemText, useRoleLabel } from "./common";

interface Props {
  account: AdminUser;
  onSaved: (message: string) => void;
  onError: (message: string) => void;
  onCancel: () => void;
}

/**
 * Roles de una cuenta (FR-023 a FR-026). El institucional conserva siempre Estudiante; el
 * invitado solo tiene Invitado. Director de programa exige elegir al menos un programa. Las
 * reglas las vuelve a aplicar el servidor (`last-admin`, `director-requires-programs`…).
 */
export function UserRolesEditor({ account, onSaved, onError, onCancel }: Props) {
  const { t } = useTranslation();
  const roleLabel = useRoleLabel();
  const save = useAdminSetUserRoles();
  const legend = useId();
  const isGuest = account.kind === "guest";
  const [roles, setRoles] = useState<Set<Role>>(() => new Set(account.roles));
  const [programs, setPrograms] = useState<Set<string>>(
    () => new Set((account.director_programs ?? []).map((program) => program.id)),
  );
  const directs = roles.has("program_director");
  const catalog = useAdminListPrograms(
    { page: 1, page_size: 100 },
    { query: { enabled: directs } },
  );
  const name = account.display_name ?? account.email ?? "";
  const available: Role[] = isGuest ? ["guest"] : ROLE_ORDER.filter((role) => role !== "guest");

  function toggle<T>(set: Set<T>, value: T): Set<T> {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  }

  async function submit() {
    const ordered = ROLE_ORDER.filter((role) => roles.has(role));
    try {
      await save.mutateAsync({
        userId: account.id,
        data: {
          roles: ordered,
          director_program_ids: directs ? [...programs] : [],
        },
      });
    } catch (problem) {
      onError(problemText(problem));
      return;
    }
    onSaved(t("admin.users.rolesSaved", { name }));
  }

  return (
    <fieldset aria-labelledby={legend} className="mt-3 rounded-md border p-4">
      <legend id={legend} className="px-1 font-semibold">
        {t("admin.users.rolesOf", { name })}
      </legend>
      {available.map((role) => {
        const locked = role === "guest" || (role === "student" && !isGuest);
        return (
          <label key={role} className="flex min-h-11 items-center gap-3">
            <input
              type="checkbox"
              className="size-5"
              checked={roles.has(role)}
              disabled={locked}
              onChange={() => setRoles((current) => toggle(current, role))}
            />
            {roleLabel(role)}
          </label>
        );
      })}

      {directs ? (
        <div className="ml-8 mt-2">
          <p className="mb-1 text-sm font-medium">{t("admin.users.directorPrograms")}</p>
          {catalog.data?.items.map((program) => (
            <label key={program.id} className="flex min-h-11 items-center gap-3">
              <input
                type="checkbox"
                className="size-5"
                checked={programs.has(program.id)}
                onChange={() => setPrograms((current) => toggle(current, program.id))}
              />
              {`${program.name} (${program.campus})`}
            </label>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex gap-2">
        <Button type="button" disabled={save.isPending} onClick={() => void submit()}>
          {t("admin.users.saveRoles")}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          {t("invitations.actions.cancel")}
        </Button>
      </div>
    </fieldset>
  );
}
