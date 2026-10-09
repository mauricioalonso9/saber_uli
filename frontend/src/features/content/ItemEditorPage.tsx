import { useQueryClient } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { getGetItemQueryKey, useGetItem } from "@/api/content/items";
import type { ItemVersion } from "@/api/content/model";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { ContentPagePlaceholder } from "@/features/content/ContentPagePlaceholder";
import { ReviewActions } from "@/features/content/ReviewActions";
import { ContentView } from "@/shared/content/ContentView";

function VersionView({ version, label }: { version: ItemVersion; label: string }) {
  const { t } = useTranslation();
  const content = version.content;
  return (
    <section aria-label={label} className="space-y-2">
      <h2 className="text-lg font-semibold">
        {label} · {t("content.version", { number: version.number })} ·{" "}
        {t(`content.states.${version.state}`)}
      </h2>
      {content.context_code ? (
        <p className="text-sm text-muted-foreground">
          {t("content.fields.context")}: {content.context_code}
        </p>
      ) : null}
      <ContentView
        kind={content.options ? "selection" : content.rubric_id ? "writing_prompt" : "matching"}
        stem_md={content.stem_md}
        options={content.options}
        answer_key={content.answer_key}
        prompt_context_md={content.prompt_context_md}
        explanation_md={content.explanation_md}
        showFeedback
      />
    </section>
  );
}

/**
 * Página de un ítem. En US2 muestra su contenido (versión abierta y publicada) con la
 * retroalimentación y las acciones de revisión; el editor llega con US3.
 */
export function ItemEditorPage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false });
  const code = params.code;
  const queryClient = useQueryClient();
  const query = useGetItem(code ?? "", { query: { enabled: Boolean(code) } });

  if (!code) return <ContentPagePlaceholder titleKey="content.pages.item" />;
  const item = query.data;
  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">
        {t("content.pages.item")} {code}
      </h1>
      <ReauthAlert error={query.error} returnTo={`/banco/items/${code}`} />
      {query.isError && !isReauth(query.error) ? (
        <p role="alert">{problemText(query.error)}</p>
      ) : null}
      {item ? (
        <>
          {item.origin === "ai" ? <p>{t("content.review.aiOrigin")}</p> : null}
          {item.last_review_comment ? (
            <p className="rounded-md border border-amber-300 bg-amber-50 p-3">
              {t("content.review.lastComment")}: {item.last_review_comment}
            </p>
          ) : null}
          <ReviewActions
            item={item}
            onChanged={() =>
              void queryClient.invalidateQueries({ queryKey: getGetItemQueryKey(code) })
            }
          />
          {item.open ? <VersionView version={item.open} label={t("content.openVersion")} /> : null}
          {item.published ? (
            <VersionView version={item.published} label={t("content.publishedVersion")} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
