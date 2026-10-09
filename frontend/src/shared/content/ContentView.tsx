import { useId } from "react";
import { useTranslation } from "react-i18next";

import { MarkdownView } from "@/shared/content/MarkdownView";
import { cn } from "@/shared/lib/utils";

export interface ContentOption {
  key: string;
  text: string;
  correct?: boolean;
  feedback?: string;
}

export interface ContentContext {
  kind: "text" | "table" | "image" | "shared_options";
  title: string;
  body_md?: string | null;
  image?: { src: string; alt: string } | null;
  shared_options?: ContentOption[] | null;
}

export interface ContentViewProps {
  kind: "selection" | "matching" | "writing_prompt";
  stem_md: string;
  context?: ContentContext | null;
  options?: ContentOption[] | null;
  /** Emparejamiento: clave correcta entre las opciones compartidas del contexto. */
  answer_key?: string | null;
  /** Consigna de escritura: el contexto propio de la consigna. */
  prompt_context_md?: string | null;
  explanation_md?: string | null;
  /** Muestra cuál es la correcta, la retroalimentación de cada opción y la explicación. */
  showFeedback?: boolean;
  className?: string;
}

/**
 * Un ítem tal como lo ve el estudiante (research R-17; FR-025). La vista previa del docente
 * (002) y la práctica (003) usan este mismo componente, así la vista previa es fiel. Con
 * `showFeedback` se ve la retroalimentación de cada opción (FR-006).
 */
export function ContentView({
  kind,
  stem_md,
  context,
  options,
  answer_key,
  prompt_context_md,
  explanation_md,
  showFeedback = false,
  className,
}: ContentViewProps) {
  const { t } = useTranslation();
  const optionsLabel = useId();
  const explanationLabel = useId();
  const shown: ContentOption[] =
    kind === "matching"
      ? (context?.shared_options ?? []).map((option) => ({
          ...option,
          correct: option.key === answer_key,
        }))
      : (options ?? []);

  return (
    <article className={cn("space-y-4", className)}>
      {context && (
        <section aria-labelledby={`${optionsLabel}-context`} className="rounded-md bg-muted/40 p-3">
          <h2 id={`${optionsLabel}-context`} className="mb-2 font-semibold">
            {context.title}
          </h2>
          {context.image && (
            <img
              src={context.image.src}
              alt={context.image.alt}
              className="mb-3 h-auto max-w-full rounded"
            />
          )}
          {context.body_md && <MarkdownView markdown={context.body_md} />}
        </section>
      )}
      {kind === "writing_prompt" && prompt_context_md && (
        <section className="rounded-md bg-muted/40 p-3">
          <MarkdownView markdown={prompt_context_md} />
        </section>
      )}
      <MarkdownView markdown={stem_md} className="font-medium" />
      {kind !== "writing_prompt" && shown.length > 0 && (
        <>
          <h3 id={optionsLabel} className="sr-only">
            {t("content.view.options")}
          </h3>
          <ol aria-labelledby={optionsLabel} className="space-y-2">
            {shown.map((option) => (
              <li
                key={option.key}
                className={cn(
                  "rounded-md border border-border p-3",
                  showFeedback && option.correct && "border-green-700 bg-green-50",
                )}
              >
                <span className="mr-2 font-bold">{option.key}</span>
                <span>{option.text}</span>
                {showFeedback && (
                  <div className="mt-2 text-sm">
                    {option.correct && (
                      <p className="font-semibold text-green-800">
                        {t("content.view.correctAnswer")}
                      </p>
                    )}
                    {option.feedback && <MarkdownView markdown={option.feedback} />}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
      {showFeedback && explanation_md && (
        <section aria-labelledby={explanationLabel} className="rounded-md border border-border p-3">
          <h3 id={explanationLabel} className="mb-1 font-semibold">
            {t("content.view.explanation")}
          </h3>
          <MarkdownView markdown={explanation_md} />
        </section>
      )}
    </article>
  );
}
