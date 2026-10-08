import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  getAdminListProgramsQueryKey,
  useAdminCreateProgram,
  useAdminListPrograms,
  useAdminUpdateProgram,
} from "@/api/admin";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

import { Feedback, ReauthAlert, isReauth, problemText } from "./common";

const CODE = /^[A-Z0-9-]{2,20}$/;

/** Catálogo de programas (FR-028). La carga masiva es el comando `import-programs`. */
export function ProgramsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const list = useAdminListPrograms({ page: 1, page_size: 100 });
  const create = useAdminCreateProgram();
  const update = useAdminUpdateProgram();
  const ids = { title: useId(), code: useId(), name: useId(), campus: useId() };
  const [values, setValues] = useState({ code: "", name: "", campus: "" });
  const [errors, setErrors] = useState<Partial<Record<keyof typeof values, string>>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    void queryClient.invalidateQueries({ queryKey: getAdminListProgramsQueryKey() });

  async function submit() {
    setMessage(null);
    setError(null);
    const data = {
      code: values.code.trim(),
      name: values.name.trim(),
      campus: values.campus.trim(),
    };
    const found: typeof errors = {};
    if (!CODE.test(data.code)) found.code = t("admin.programs.errors.code");
    if (data.name.length < 3 || data.name.length > 200)
      found.name = t("admin.programs.errors.name");
    if (data.campus.length < 2 || data.campus.length > 100) {
      found.campus = t("admin.programs.errors.campus");
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    try {
      await create.mutateAsync({ data });
    } catch (problem) {
      setError(problemText(problem));
      return;
    }
    setMessage(t("admin.programs.created", { name: data.name }));
    setValues({ code: "", name: "", campus: "" });
    refresh();
  }

  async function toggle(programId: string, active: boolean, label: string) {
    setMessage(null);
    setError(null);
    try {
      await update.mutateAsync({ programId, data: { active } });
    } catch (problem) {
      setError(problemText(problem));
      return;
    }
    setMessage(t(active ? "admin.programs.activated" : "admin.programs.deactivated", { label }));
    refresh();
  }

  const field = (key: keyof typeof values, id: string, maxLength: number) => (
    <div>
      <Label htmlFor={id}>{t(`admin.programs.${key}`)}</Label>
      <Input
        id={id}
        className="h-11"
        maxLength={maxLength}
        value={values[key]}
        aria-invalid={errors[key] ? true : undefined}
        aria-describedby={errors[key] ? `${id}-error` : undefined}
        onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))}
      />
      {errors[key] ? (
        <p id={`${id}-error`} className="mt-1 text-sm text-destructive">
          {errors[key]}
        </p>
      ) : null}
    </div>
  );

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("admin.programs.title")}</h1>
      <ReauthAlert error={list.error} returnTo="/admin/programas" />
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
          {t("admin.programs.createTitle")}
        </h2>
        {field("code", ids.code, 20)}
        {field("name", ids.name, 200)}
        {field("campus", ids.campus, 100)}
        <Button type="submit" className="h-11" disabled={create.isPending}>
          {t("admin.programs.create")}
        </Button>
      </form>

      {list.isError && !isReauth(list.error) ? <p role="alert">{problemText(list.error)}</p> : null}
      {list.data ? (
        <div className="overflow-x-auto">
          <table aria-label={t("admin.programs.table")} className="w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                {["code", "name", "campus", "state", "actions"].map((column) => (
                  <th key={column} scope="col" className="py-2 pr-3">
                    {t(`admin.programs.columns.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((program) => {
                const label = `${program.name} (${program.campus})`;
                return (
                  <tr key={program.id} className="border-b">
                    <td className="py-2 pr-3">{program.code}</td>
                    <td className="py-2 pr-3">{program.name}</td>
                    <td className="py-2 pr-3">{program.campus}</td>
                    <td className="py-2 pr-3">
                      {program.active ? t("admin.programs.active") : t("admin.programs.inactive")}
                    </td>
                    <td className="py-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        aria-label={t(
                          program.active
                            ? "admin.programs.deactivateOf"
                            : "admin.programs.activateOf",
                          { label },
                        )}
                        onClick={() => void toggle(program.id, !program.active, label)}
                      >
                        {program.active
                          ? t("admin.programs.deactivate")
                          : t("admin.programs.activate")}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
