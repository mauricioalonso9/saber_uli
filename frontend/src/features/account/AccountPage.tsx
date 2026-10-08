import { useQueryClient } from "@tanstack/react-query";
import { Link, useRouteContext } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ProfileUpdate } from "@/api/model";
import { getGetMyProfileQueryKey, useGetMyProfile, useUpdateMyProfile } from "@/api/me";
import { useListActivePrograms } from "@/api/programs";
import { DeleteAccountSection } from "@/features/account/DeleteAccountSection";
import { SessionsSection } from "@/features/account/SessionsSection";
import { DirectoryData } from "@/features/profile/DirectoryData";
import { ProfileForm } from "@/features/profile/ProfileForm";
import { ApiProblem } from "@/shared/api/http";
import { GENERIC_MESSAGE } from "@/shared/api/problem-messages";
import { refreshQueries } from "@/shared/api/refresh";

/**
 * Mi cuenta (FR-021, FR-032, FR-037a): editar el perfil, llegar a la autorización y a mis datos,
 * ver y cerrar las sesiones abiertas, y solicitar la supresión de la cuenta.
 */
export function AccountPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { session, getSession } = useRouteContext({ from: "__root__" });
  const me = session?.kind === "authenticated" ? session.me : null;
  const isGuest = me?.kind === "guest";
  const profile = useGetMyProfile();
  const programs = useListActivePrograms({ query: { enabled: me !== null && !isGuest } });
  const update = useUpdateMyProfile();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const formTitle = useId();

  async function save(data: ProfileUpdate) {
    setError(null);
    setSaved(false);
    try {
      await update.mutateAsync({ data });
    } catch (problem) {
      setError(problem instanceof ApiProblem ? problem.message : GENERIC_MESSAGE);
      return;
    }
    await refreshQueries(queryClient, getGetMyProfileQueryKey());
    // El nombre de un invitado es su nombre visible: `/me` cambia.
    getSession.invalidate?.();
    setSaved(true);
  }

  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{t("account.title")}</h1>
      {me && !isGuest ? <DirectoryData me={me} /> : null}

      <h2 id={formTitle} className="mb-3 text-lg font-semibold">
        {t("account.profile")}
      </h2>
      {profile.isPending || (!isGuest && programs.isPending) ? (
        <p role="status">{t("profile.loading")}</p>
      ) : null}
      {saved ? (
        <p role="status" className="mb-4 rounded-md border border-green-300 bg-green-50 p-3">
          {t("account.saved")}
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
          labelledBy={formTitle}
          submitLabel={t("account.save")}
          pending={update.isPending}
          onSubmit={save}
        />
      ) : null}

      <ul className="mt-8 flex flex-col gap-2">
        <li>
          <Link to="/mi-cuenta/autorizacion" className="underline">
            {t("nav.consent")}
          </Link>
        </li>
        <li>
          <Link to="/mi-cuenta/datos" className="underline">
            {t("accountData.title")}
          </Link>
        </li>
      </ul>

      <SessionsSection />
      <DeleteAccountSection />
    </section>
  );
}
