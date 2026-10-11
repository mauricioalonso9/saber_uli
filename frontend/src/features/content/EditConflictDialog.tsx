import { useEffect, useId, useRef } from "react";
import { useTranslation } from "react-i18next";

import type { Item, ItemContent } from "@/api/content/model";
import { ContentView } from "@/shared/content/ContentView";
import { Button } from "@/shared/ui/button";

/**
 * Conflicto de edición (412 `edit-conflict`; FR-027, research R-09): otra persona guardó mientras
 * se editaba. Muestra los dos contenidos y deja conservar los cambios propios (se guardan sobre
 * la revisión actual) o descartarlos (se carga la versión actual). Nada se sobrescribe sin que la
 * persona lo decida.
 */
export function EditConflictDialog({
  open,
  mine,
  current,
  onKeepMine,
  onDiscard,
}: {
  open: boolean;
  mine: ItemContent;
  current: Item;
  onKeepMine: () => void;
  onDiscard: () => void;
}) {
  const { t } = useTranslation();
  const titleId = useId();
  const title = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (open) title.current?.focus();
  }, [open]);

  if (!open) return null;
  const theirs = (current.open ?? current.published)?.content;
  const view = (content: ItemContent) => (
    <ContentView
      kind={current.kind}
      stem_md={content.stem_md}
      options={content.options}
      answer_key={content.answer_key}
      prompt_context_md={content.prompt_context_md}
      explanation_md={content.explanation_md}
      showFeedback
    />
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="max-h-full w-full max-w-5xl overflow-auto rounded-lg bg-background p-6 shadow-lg"
      >
        <h2 id={titleId} ref={title} tabIndex={-1} className="text-xl font-semibold">
          {t("content.conflict.title")}
        </h2>
        <p className="mt-2">{t("content.conflict.intro")}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <section aria-label={t("content.conflict.mine")} className="rounded-md border p-3">
            <h3 className="mb-2 font-semibold">{t("content.conflict.mine")}</h3>
            {view(mine)}
          </section>
          <section aria-label={t("content.conflict.current")} className="rounded-md border p-3">
            <h3 className="mb-2 font-semibold">{t("content.conflict.current")}</h3>
            {theirs ? view(theirs) : null}
          </section>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" onClick={onKeepMine}>
            {t("content.conflict.keep")}
          </Button>
          <Button type="button" variant="outline" onClick={onDiscard}>
            {t("content.conflict.discard")}
          </Button>
        </div>
      </div>
    </div>
  );
}
