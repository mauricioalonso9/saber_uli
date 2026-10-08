import { Link } from "@tanstack/react-router";
import { type ReactNode, useId } from "react";
import { useTranslation } from "react-i18next";

import type { PersonalDataExport } from "@/api/model";
import { useExportMyData } from "@/api/me";
import { DeleteAccountSection } from "@/features/account/DeleteAccountSection";
import { useRoleLabel } from "@/features/admin/common";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { formatDate, formatDateTime, formatDay } from "@/shared/lib/dates";
import { Button } from "@/shared/ui/button";

/** Descarga la copia tal como la entregó el servidor (FR-031). */
function download(data: PersonalDataExport) {
  const day = dayInBogota(data.generated_at);
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `saber-uli-mis-datos-${day}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Fecha `AAAA-MM-DD` en Colombia, como el nombre de archivo del servidor. */
function dayInBogota(iso: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota" }).format(new Date(iso));
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="mb-6">
      <h2 id={id} className="mb-2 text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="mb-1 flex flex-wrap gap-x-2">
      <dt className="font-medium">{label}:</dt>
      <dd>{value}</dd>
    </div>
  );
}

/**
 * Mis datos (FR-031; escenarios 8.1 y 8.2): todo lo que se guarda de la persona, la descarga en
 * JSON, cómo corregir los datos del directorio y la solicitud de supresión (FR-032).
 */
export function MyDataPage() {
  const { t } = useTranslation();
  const roleLabel = useRoleLabel();
  const exported = useExportMyData();
  const noteTitle = useId();
  const none = t("accountData.none");

  if (exported.isError) {
    return (
      <section>
        <h1 className="mb-4 text-2xl font-bold">{t("accountData.title")}</h1>
        <p role="alert">
          {exported.error instanceof ApiProblem ? exported.error.message : GENERIC_MESSAGE}
        </p>
      </section>
    );
  }
  const data = exported.data;

  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t("accountData.title")}</h1>
      <p className="mb-4">{t("accountData.intro")}</p>
      {!data ? <p role="status">{t("accountData.loading")}</p> : null}
      {data ? (
        <>
          <Button type="button" className="mb-6" onClick={() => download(data)}>
            {t("accountData.download")}
          </Button>

          <Section title={t("accountData.identity")}>
            <dl>
              <Field
                label={t("accountData.fields.name")}
                value={data.identity.display_name ?? none}
              />
              <Field label={t("accountData.fields.email")} value={data.identity.email ?? none} />
              <Field
                label={t("accountData.fields.kind")}
                value={t(`accountData.kinds.${data.identity.kind ?? "institutional"}`)}
              />
              {data.identity.created_at ? (
                <Field
                  label={t("accountData.fields.createdAt")}
                  value={formatDate(data.identity.created_at)}
                />
              ) : null}
              {data.identity.last_login_at ? (
                <Field
                  label={t("accountData.fields.lastLogin")}
                  value={formatDateTime(data.identity.last_login_at)}
                />
              ) : null}
            </dl>
          </Section>

          <aside
            role="note"
            aria-labelledby={noteTitle}
            className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-4 text-amber-950"
          >
            <h2 id={noteTitle} className="mb-2 font-semibold">
              {t("accountData.fix.title")}
            </h2>
            <p className="mb-2">{data.identity.source_note}</p>
            <Link to="/mi-cuenta" className="underline">
              {t("accountData.fix.editProfile")}
            </Link>
          </aside>

          <Section title={t("accountData.profile")}>
            <dl>
              <Field
                label={t("accountData.fields.program")}
                value={
                  data.profile?.program
                    ? `${data.profile.program.name} (${data.profile.program.campus})`
                    : none
                }
              />
              <Field
                label={t("accountData.fields.semester")}
                value={data.profile?.semester ?? none}
              />
              <Field
                label={t("accountData.fields.examDate")}
                value={
                  data.profile?.expected_exam_date
                    ? formatDay(data.profile.expected_exam_date)
                    : none
                }
              />
              <Field
                label={t("accountData.fields.dailyGoal")}
                value={data.profile ? t(`profile.goals.${data.profile.daily_goal}`) : none}
              />
            </dl>
          </Section>

          {data.invitation ? (
            <Section title={t("accountData.invitation")}>
              <dl>
                {data.invitation.accepted_at ? (
                  <Field
                    label={t("accountData.fields.acceptedAt")}
                    value={formatDate(data.invitation.accepted_at)}
                  />
                ) : null}
                {data.invitation.access_expires_at ? (
                  <Field
                    label={t("accountData.fields.accessUntil")}
                    value={formatDate(data.invitation.access_expires_at)}
                  />
                ) : null}
              </dl>
            </Section>
          ) : null}

          <Section title={t("accountData.roles")}>
            <p>{data.roles.map(roleLabel).join(", ")}</p>
          </Section>

          <Section title={t("accountData.groups")}>
            {data.groups?.length ? (
              <ul className="list-disc pl-6">
                {data.groups.map((group) => (
                  <li key={group}>{group}</li>
                ))}
              </ul>
            ) : (
              <p>{t("accountData.noGroups")}</p>
            )}
          </Section>

          <Section title={t("accountData.consents")}>
            <ul className="list-disc pl-6">
              {data.consents.map((consent) => (
                <li key={consent.id}>
                  {t(`consentSettings.decision.${consent.decision}`, {
                    version: consent.policy_version,
                    date: formatDateTime(consent.decided_at),
                  })}
                </li>
              ))}
            </ul>
          </Section>
        </>
      ) : null}

      <DeleteAccountSection />
    </section>
  );
}
