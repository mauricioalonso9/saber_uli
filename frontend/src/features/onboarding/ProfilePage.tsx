import { useQueryClient } from "@tanstack/react-query";
import { useRouteContext, useRouter } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ProfileUpdate } from "@/api/model";
import { getGetMyProfileQueryKey, useGetMyProfile, useUpdateMyProfile } from "@/api/me";
import { useListActivePrograms } from "@/api/programs";
import { DirectoryData } from "@/features/profile/DirectoryData";
import { ProfileForm } from "@/features/profile/ProfileForm";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { refreshQueries } from "@/shared/api/refresh";

/**
 * Perfil del primer ingreso (FR-019, FR-020): el último paso antes de `/inicio`. El institucional
 * elige programa, semestre, fecha de su prueba y meta; el invitado, nombre, meta y, si quiere, la
 * fecha.
 */
export function ProfilePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { session, getSession } = useRouteContext({ from: "__root__" });
  const me = session?.kind === "authenticated" ? session.me : null;
  const isGuest = me?.kind === "guest";
  const profile = useGetMyProfile();
  const programs = useListActivePrograms({ query: { enabled: me !== null && !isGuest } });
  const update = useUpdateMyProfile();
  const [error, setError] = useState<string | null>(null);
  const title = useId();

  async function save(data: ProfileUpdate) {
    setError(null);
    try {
      await update.mutateAsync({ data });
    } catch (problem) {
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
      return;
    }
    await refreshQueries(queryClient, getGetMyProfileQueryKey());
    getSession.invalidate?.();
    await router.navigate({ to: "/inicio" });
  }

  const loading = profile.isPending || (!isGuest && programs.isPending);
  const failed = profile.error ?? (isGuest ? null : programs.error);

  return (
    <section>
      <h1 id={title} className="mb-2 text-2xl font-bold">
        {t("profile.title")}
      </h1>
      <p className="mb-6">{isGuest ? t("profile.introGuest") : t("profile.intro")}</p>
      {me && !isGuest ? <DirectoryData me={me} /> : null}
      {loading ? <p role="status">{t("profile.loading")}</p> : null}
      {failed ? (
        <p role="alert" className="text-destructive">
          {failed instanceof ApiProblem ? failed.message : GENERIC_MESSAGE}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mb-4 text-destructive">
          {error}
        </p>
      ) : null}
      {me && profile.data && (isGuest || programs.data) ? (
        <ProfileForm
          kind={me.kind}
          profile={profile.data}
          programs={programs.data ?? []}
          labelledBy={title}
          submitLabel={t("profile.saveAndContinue")}
          pending={update.isPending}
          onSubmit={save}
        />
      ) : null}
    </section>
  );
}
