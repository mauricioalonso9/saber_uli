import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ItemContent, ItemKind } from "@/api/content/model";
import { type ContentContext, ContentView } from "@/shared/content/ContentView";
import { cn } from "@/shared/lib/utils";

type Tab = "student" | "feedback";

/**
 * Vista previa del ítem (FR-025; research R-17): el mismo `ContentView` de la práctica, en un
 * marco del tamaño de un celular (360 × 800) y sin revelar la respuesta; la pestaña
 * "Retroalimentación" muestra la de cada opción y la explicación general.
 */
export function ItemPreview({
  kind,
  content,
  context,
}: {
  kind: ItemKind;
  content: ItemContent;
  context?: ContentContext | null;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("student");
  const base = useId();
  const tabs: Tab[] = ["student", "feedback"];

  const view = (showFeedback: boolean) => (
    <ContentView
      kind={kind}
      stem_md={content.stem_md}
      context={context}
      options={content.options}
      answer_key={content.answer_key}
      prompt_context_md={content.prompt_context_md}
      explanation_md={content.explanation_md}
      showFeedback={showFeedback}
    />
  );

  return (
    <div className="space-y-3">
      <div role="tablist" aria-label={t("content.preview.tabs")} className="flex gap-2">
        {tabs.map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            id={`${base}-${name}-tab`}
            aria-selected={tab === name}
            aria-controls={`${base}-${name}-panel`}
            tabIndex={tab === name ? 0 : -1}
            onClick={() => setTab(name)}
            className={cn(
              "rounded-md border px-3 py-1 text-sm",
              tab === name ? "border-primary bg-primary text-primary-foreground" : "border-input",
            )}
          >
            {t(`content.preview.${name}`)}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`${base}-${tab}-panel`}
        aria-labelledby={`${base}-${tab}-tab`}
        tabIndex={0}
      >
        {tab === "student" ? (
          <section
            aria-label={t("content.preview.frame")}
            // Región que se desplaza: debe poder recorrerse con el teclado (WCAG 2.1.1).
            // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
            tabIndex={0}
            style={{ width: "360px", height: "800px" }}
            className="max-w-full overflow-auto rounded-3xl border-8 border-foreground/80 bg-background p-4"
          >
            {view(false)}
          </section>
        ) : (
          view(true)
        )}
      </div>
    </div>
  );
}
