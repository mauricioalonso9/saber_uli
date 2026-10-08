import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Settings, SettingsPatch } from "@/api/model";
import {
  getAdminGetSettingsQueryKey,
  useAdminGetSettings,
  useAdminUpdateSettings,
} from "@/api/admin";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

import { Feedback, ReauthAlert, isReauth, problemText } from "./common";

/** Rangos del contrato (`Settings`). */
const FIELDS: { key: keyof Settings; min: number; max: number }[] = [
  { key: "teacher_max_access_days", min: 1, max: 730 },
  { key: "default_guest_access_days", min: 1, max: 730 },
  { key: "invitation_link_ttl_days", min: 1, max: 30 },
  { key: "sign_in_link_ttl_minutes", min: 5, max: 60 },
];

/** Parámetros (R-29; FR-006a): plazos de invitados y vigencia de los enlaces. */
export function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const current = useAdminGetSettings();
  const update = useAdminUpdateSettings();
  const baseId = useId();
  const [values, setValues] = useState<Record<keyof Settings, string> | null>(null);
  const [errors, setErrors] = useState<Partial<Record<keyof Settings, string>>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (current.data && values === null) {
      const data = current.data;
      setValues(
        Object.fromEntries(FIELDS.map(({ key }) => [key, String(data[key])])) as Record<
          keyof Settings,
          string
        >,
      );
    }
  }, [current.data, values]);

  async function submit() {
    if (!values || !current.data) return;
    setMessage(null);
    setError(null);
    const found: typeof errors = {};
    const changes: SettingsPatch = {};
    for (const { key, min, max } of FIELDS) {
      const value = Number(values[key]);
      if (!Number.isInteger(value) || value < min || value > max) {
        found[key] = t("admin.settings.range", { min, max });
      } else if (value !== current.data[key]) {
        changes[key] = value;
      }
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    if (Object.keys(changes).length === 0) {
      setMessage(t("admin.settings.noChanges"));
      return;
    }
    try {
      await update.mutateAsync({ data: changes });
    } catch (problem) {
      setError(problemText(problem));
      return;
    }
    setMessage(t("admin.settings.saved"));
    void queryClient.invalidateQueries({ queryKey: getAdminGetSettingsQueryKey() });
  }

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("admin.settings.title")}</h1>
      <ReauthAlert error={current.error} returnTo="/admin/parametros" />
      {current.isError && !isReauth(current.error) ? (
        <p role="alert">{problemText(current.error)}</p>
      ) : null}
      <Feedback message={message} error={error} />
      {values ? (
        <form
          noValidate
          className="max-w-md space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          {FIELDS.map(({ key, min, max }) => {
            const id = `${baseId}-${key}`;
            return (
              <div key={key}>
                <Label htmlFor={id}>{t(`admin.settings.fields.${key}`)}</Label>
                <Input
                  id={id}
                  type="number"
                  inputMode="numeric"
                  min={min}
                  max={max}
                  className="h-11"
                  value={values[key]}
                  aria-invalid={errors[key] ? true : undefined}
                  aria-describedby={errors[key] ? `${id}-error` : undefined}
                  onChange={(event) =>
                    setValues((v) => (v ? { ...v, [key]: event.target.value } : v))
                  }
                />
                {errors[key] ? (
                  <p id={`${id}-error`} className="mt-1 text-sm text-destructive">
                    {errors[key]}
                  </p>
                ) : null}
              </div>
            );
          })}
          <Button type="submit" className="h-11" disabled={update.isPending}>
            {t("admin.settings.save")}
          </Button>
        </form>
      ) : null}
    </section>
  );
}
