import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { Me } from "@/api/model";

/** Nombre y correo del directorio de Unilibre: se muestran, no se editan (FR-021). */
export function DirectoryData({ me }: { me: Me }) {
  const { t } = useTranslation();
  const title = useId();
  return (
    <section aria-labelledby={title} className="mb-6 rounded-md border p-4">
      <h2 id={title} className="mb-2 text-lg font-semibold">
        {t("profile.directory.title")}
      </h2>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
        <dt className="font-medium">{t("profile.directory.name")}</dt>
        <dd>{me.display_name}</dd>
        <dt className="font-medium">{t("profile.directory.email")}</dt>
        <dd className="break-all">{me.email}</dd>
      </dl>
      <p className="mt-2 text-sm text-muted-foreground">{t("profile.directory.note")}</p>
    </section>
  );
}
