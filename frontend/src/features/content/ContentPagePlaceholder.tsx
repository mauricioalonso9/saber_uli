import { useTranslation } from "react-i18next";

/** Página provisional del banco mientras su historia no está implementada (T034). */
export function ContentPagePlaceholder({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t(titleKey)}</h1>
      <p>{t("content.placeholder")}</p>
    </section>
  );
}
