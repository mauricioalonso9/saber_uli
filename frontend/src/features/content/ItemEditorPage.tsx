import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "@tanstack/react-router";
import { type ReactNode, useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  createItem,
  getGetItemQueryKey,
  saveItemDraft,
  submitItem,
  useGetItem,
} from "@/api/content/items";
import type {
  ContentModule,
  Item,
  ItemContent,
  ItemKind,
  ItemVersion,
  ModuleCodeValue,
  Option,
  TaxonomyNode,
  TaxonomyTags,
} from "@/api/content/model";
import { useGetContext } from "@/api/content/contexts";
import { useListContentModules, useListRubrics } from "@/api/content/taxonomy";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { EditConflictDialog } from "@/features/content/EditConflictDialog";
import { ItemHistory } from "@/features/content/ItemHistory";
import { ItemPreview } from "@/features/content/ItemPreview";
import { ItemStatistics } from "@/features/content/ItemStatistics";
import { useObjectUrl } from "@/features/content/MediaUpload";
import { ReviewActions } from "@/features/content/ReviewActions";
import { type ContentIssue, validateItem } from "@/features/content/schemas";
import { ApiProblem } from "@/shared/api/http";
import type { ContentContext } from "@/shared/content/ContentView";
import { Button } from "@/shared/ui/button";

const FIELD =
  "mt-1 block w-full rounded-md border border-input bg-background px-3 py-2 text-base aria-[invalid=true]:border-red-600";
const TAG_KINDS = [
  "competence",
  "assertion",
  "evidence",
  "component",
  "situation",
  "part",
] as const;
type TagKind = (typeof TAG_KINDS)[number];
const PARENT: Partial<Record<TagKind, TagKind>> = {
  assertion: "competence",
  evidence: "assertion",
};

function emptyContent(): ItemContent {
  return {
    difficulty: "medium",
    context_code: null,
    taxonomy: {},
    stem_md: "",
    options: null,
    answer_key: null,
    explanation_md: "",
    prompt_context_md: null,
    rubric_id: null,
  };
}

function partOf(module: ContentModule | undefined, tags: TaxonomyTags): TaxonomyNode | undefined {
  return module?.nodes.find((node) => node.id === tags.part_id && node.kind === "part");
}

/** El tipo sale del módulo y de la parte: CE escribe, la parte 1 de Inglés empareja. */
function kindFor(module: ContentModule | undefined, tags: TaxonomyTags): ItemKind {
  if (module?.question_type === "writing") return "writing_prompt";
  return partOf(module, tags)?.part_format === "matching" ? "matching" : "selection";
}

function optionCount(module: ContentModule | undefined, tags: TaxonomyTags): number {
  return partOf(module, tags)?.part_options ?? module?.options_per_item ?? 4;
}

/** Ajusta las opciones al tipo y a la cantidad que pide el módulo o la parte. */
function normalized(content: ItemContent, kind: ItemKind, count: number): ItemContent {
  if (kind !== "selection") return { ...content, options: null };
  const current = content.options ?? [];
  const options: Option[] = Array.from({ length: count }, (_, index) => {
    const key = String.fromCharCode(65 + index);
    return current[index] ?? { key, text: "", correct: false, feedback: "" };
  });
  return { ...content, options, answer_key: null };
}

/** Mensajes por campo; un campo puede tener varios. */
function byField(issues: { field: string; message: string }[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const { field, message } of issues) {
    map.set(field, map.has(field) ? `${map.get(field)} ${message}` : message);
  }
  return map;
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="font-medium">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function invalid(id: string, error: string | undefined) {
  return error ? { "aria-invalid": true, "aria-describedby": `${id}-error` } : {};
}

type Action = "save" | "submit";

/**
 * Editor de ítems (US3; FR-015, FR-016, FR-024, FR-025, FR-027). Los campos dependen del módulo y
 * de la parte. Guardar acepta un borrador incompleto; enviar a revisión aplica antes las reglas
 * del banco (`schemas.ts`) y muestra cada error junto a su campo. Cada cambio envía la revisión
 * que la persona está viendo (`If-Match`); un 412 abre el diálogo de conflicto.
 */
export function ItemEditor({ item, onSaved }: { item?: Item; onSaved?: (item: Item) => void }) {
  const { t } = useTranslation();
  const base = useId();
  const modules = useListContentModules().data?.items ?? [];
  const [moduleCode, setModuleCode] = useState<ModuleCodeValue | "">(item?.module ?? "");
  const module = modules.find((m) => m.code === moduleCode);
  const rubrics = useListRubrics({ query: { enabled: module?.question_type === "writing" } });
  const [code, setCode] = useState(item?.code ?? "");
  const [revision, setRevision] = useState(item?.revision ?? null);
  const [current, setCurrent] = useState(item);
  const [content, setContent] = useState<ItemContent>(
    () => (item?.open ?? item?.published)?.content ?? emptyContent(),
  );
  const [keepInReview, setKeepInReview] = useState(false);
  const [errors, setErrors] = useState<Map<string, string>>(new Map());
  const [status, setStatus] = useState<string | null>(null);
  const [alert, setAlert] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Item | null>(null);
  const [busy, setBusy] = useState(false);

  const kind = item?.kind ?? kindFor(module, content.taxonomy);
  const contextCode = content.context_code ?? "";
  const contextQuery = useGetContext(contextCode, {
    query: { enabled: /^[A-Z]{2,3}(-[A-Z0-9]+){1,3}$/.test(contextCode), retry: false },
  });
  const imageUrl = useObjectUrl(
    contextQuery.data?.kind === "image" ? contextQuery.data.media_id : null,
  );
  // Contexto vigente para la vista previa y las reglas; `null` si el código no existe.
  const context = contextCode ? (contextQuery.isError ? null : contextQuery.data) : undefined;
  const previewContext: ContentContext | null = context
    ? {
        kind: context.kind,
        title: context.title,
        body_md: context.body_md,
        image: imageUrl ? { src: imageUrl, alt: context.alt_text ?? "" } : null,
        shared_options: context.shared_options,
      }
    : null;
  const count = optionCount(module, content.taxonomy);
  const shown = useMemo(() => normalized(content, kind, count), [content, kind, count]);
  const id = (name: string) => `${base}-${name}`;

  function update(patch: Partial<ItemContent>) {
    setContent((previous) => ({ ...previous, ...patch }));
  }

  function setTag(tag: TagKind, value: string) {
    const taxonomy: TaxonomyTags = { ...content.taxonomy, [`${tag}_id`]: value || null };
    // Al cambiar una categoría, sus hijas dejan de valer.
    for (const [child, parent] of Object.entries(PARENT)) {
      if (parent === tag) taxonomy[`${child as TagKind}_id`] = null;
    }
    update({ taxonomy });
  }

  function setOption(index: number, patch: Partial<Option>) {
    const options = (shown.options ?? []).map((option, i) =>
      i === index
        ? { ...option, ...patch }
        : patch.correct
          ? { ...option, correct: false }
          : option,
    );
    update({ options });
  }

  function fail(issues: { field: string; message: string }[]) {
    setErrors(byField(issues));
    setStatus(t("content.editor.fixFields", { count: new Set(issues.map((i) => i.field)).size }));
  }

  function handle(failure: unknown) {
    if (failure instanceof ApiProblem && failure.status === 412) {
      setConflict((failure.extensions.current as Item | undefined) ?? null);
      return;
    }
    if (failure instanceof ApiProblem && failure.errors?.length) {
      fail(failure.errors);
      return;
    }
    setAlert(
      failure instanceof ApiProblem && failure.detail ? failure.detail : problemText(failure),
    );
  }

  async function save(action: Action, expected = revision): Promise<void> {
    setStatus(null);
    setAlert(null);
    if (action === "submit") {
      const issues: ContentIssue[] = module ? validateItem(kind, shown, module, { context }) : [];
      if (issues.length) {
        fail(issues);
        return;
      }
    }
    setErrors(new Map());
    setBusy(true);
    try {
      let saved: Item;
      if (!current) {
        if (!module) return;
        saved = await createItem({ code, module: module.code, kind, content: shown });
      } else {
        saved = await saveItemDraft(
          current.code,
          shown,
          keepInReview ? { keep_in_review: true } : undefined,
          { headers: { "If-Match": `"${expected}"` } },
        );
      }
      if (action === "submit") {
        saved = await submitItem(saved.code, { headers: { "If-Match": `"${saved.revision}"` } });
      }
      setCurrent(saved);
      setRevision(saved.revision);
      setKeepInReview(false);
      setStatus(
        t(
          action === "submit"
            ? "content.editor.submitted"
            : current
              ? "content.editor.saved"
              : "content.editor.created",
        ),
      );
      onSaved?.(saved);
    } catch (failure) {
      handle(failure);
    } finally {
      setBusy(false);
    }
  }

  const tagNodes = (tag: TagKind) => {
    const nodes = (module?.nodes ?? []).filter((node) => node.kind === tag);
    const parentTag = PARENT[tag];
    const parentId = parentTag ? content.taxonomy[`${parentTag}_id`] : null;
    return parentId ? nodes.filter((node) => node.parent_id === parentId) : nodes;
  };
  const presentTags = TAG_KINDS.filter((tag) => module?.nodes.some((node) => node.kind === tag));
  const nextVersion = current?.published && !current.open ? current.published.number + 1 : null;
  const error = (field: string) => errors.get(field);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_auto]">
      <form
        className="space-y-4"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void save("save");
        }}
      >
        <p role="status" aria-live="polite" className="empty:hidden rounded-md bg-muted p-3">
          {status}
        </p>
        {alert ? (
          <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
            {alert}
          </p>
        ) : null}
        {nextVersion ? (
          <p className="rounded-md border border-amber-300 bg-amber-50 p-3">
            {t("content.editor.publishedNotice", { number: nextVersion })}
          </p>
        ) : null}

        {current ? null : (
          <>
            <Field id={id("module")} label={t("content.editor.module")}>
              <select
                id={id("module")}
                className={FIELD}
                value={moduleCode}
                onChange={(event) => {
                  setModuleCode(event.target.value as ModuleCodeValue);
                  update({ taxonomy: {}, options: null, answer_key: null, rubric_id: null });
                }}
              >
                <option value="">{t("content.editor.choose")}</option>
                {modules.map((m) => (
                  <option key={m.code} value={m.code}>
                    {m.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field id={id("code")} label={t("content.editor.code")} error={error("code")}>
              <input
                id={id("code")}
                className={FIELD}
                value={code}
                onChange={(event) => setCode(event.target.value.toUpperCase())}
                {...invalid(id("code"), error("code"))}
              />
            </Field>
          </>
        )}

        {module ? (
          <>
            <Field id={id("difficulty")} label={t("content.editor.difficulty")}>
              <select
                id={id("difficulty")}
                className={FIELD}
                value={content.difficulty}
                onChange={(event) =>
                  update({ difficulty: event.target.value as ItemContent["difficulty"] })
                }
              >
                {(["low", "medium", "high"] as const).map((value) => (
                  <option key={value} value={value}>
                    {t(`content.editor.difficulties.${value}`)}
                  </option>
                ))}
              </select>
            </Field>

            {presentTags.map((tag) => {
              const field = `taxonomy.${tag}_id`;
              return (
                <Field
                  key={tag}
                  id={id(tag)}
                  label={t(`content.editor.tags.${tag}`)}
                  error={error(field)}
                >
                  <select
                    id={id(tag)}
                    className={FIELD}
                    value={content.taxonomy[`${tag}_id`] ?? ""}
                    onChange={(event) => setTag(tag, event.target.value)}
                    {...invalid(id(tag), error(field))}
                  >
                    <option value="">{t("content.editor.choose")}</option>
                    {tagNodes(tag).map((node) => (
                      <option key={node.id} value={node.id}>
                        {node.code} · {node.name}
                      </option>
                    ))}
                  </select>
                </Field>
              );
            })}

            {kind !== "writing_prompt" ? (
              <Field
                id={id("context")}
                label={t("content.editor.contextCode")}
                error={error("context_code")}
              >
                <input
                  id={id("context")}
                  className={FIELD}
                  value={content.context_code ?? ""}
                  onChange={(event) =>
                    update({ context_code: event.target.value.toUpperCase() || null })
                  }
                  {...invalid(id("context"), error("context_code"))}
                />
              </Field>
            ) : null}

            {kind === "writing_prompt" ? (
              <Field
                id={id("prompt")}
                label={t("content.editor.promptContext")}
                error={error("prompt_context_md")}
              >
                <textarea
                  id={id("prompt")}
                  rows={5}
                  className={FIELD}
                  value={content.prompt_context_md ?? ""}
                  onChange={(event) => update({ prompt_context_md: event.target.value })}
                  {...invalid(id("prompt"), error("prompt_context_md"))}
                />
              </Field>
            ) : null}

            <Field id={id("stem")} label={t("content.editor.stem")} error={error("stem_md")}>
              <textarea
                id={id("stem")}
                rows={3}
                className={FIELD}
                value={content.stem_md}
                onChange={(event) => update({ stem_md: event.target.value })}
                {...invalid(id("stem"), error("stem_md"))}
              />
            </Field>

            {kind === "selection" ? (
              <fieldset
                className="space-y-3 rounded-md border p-3"
                aria-describedby={error("options") ? `${id("options")}-error` : undefined}
              >
                <legend className="font-medium">{t("content.editor.options")}</legend>
                {error("options") ? (
                  <p id={`${id("options")}-error`} className="text-sm text-red-700">
                    {error("options")}
                  </p>
                ) : null}
                {(shown.options ?? []).map((option, index) => {
                  const text = `options[${option.key}].text`;
                  const feedback = `options[${option.key}].feedback`;
                  return (
                    <div key={option.key} className="space-y-2 border-t pt-3 first:border-t-0">
                      <Field
                        id={id(`option-${option.key}`)}
                        label={t("content.editor.optionText", { key: option.key })}
                        error={error(text)}
                      >
                        <textarea
                          id={id(`option-${option.key}`)}
                          rows={2}
                          className={FIELD}
                          value={option.text}
                          onChange={(event) => setOption(index, { text: event.target.value })}
                          {...invalid(id(`option-${option.key}`), error(text))}
                        />
                      </Field>
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          name={id("correct")}
                          checked={option.correct}
                          onChange={() => setOption(index, { correct: true })}
                        />
                        {t("content.editor.optionCorrect", { key: option.key })}
                      </label>
                      <Field
                        id={id(`feedback-${option.key}`)}
                        label={t("content.editor.optionFeedback", { key: option.key })}
                        error={error(feedback)}
                      >
                        <textarea
                          id={id(`feedback-${option.key}`)}
                          rows={2}
                          className={FIELD}
                          value={option.feedback}
                          onChange={(event) => setOption(index, { feedback: event.target.value })}
                          {...invalid(id(`feedback-${option.key}`), error(feedback))}
                        />
                      </Field>
                    </div>
                  );
                })}
              </fieldset>
            ) : null}

            {kind === "matching" ? (
              <Field
                id={id("answer")}
                label={t("content.editor.answerKey")}
                error={error("answer_key")}
              >
                <input
                  id={id("answer")}
                  className={FIELD}
                  maxLength={1}
                  value={content.answer_key ?? ""}
                  onChange={(event) =>
                    update({ answer_key: event.target.value.toUpperCase() || null })
                  }
                  {...invalid(id("answer"), error("answer_key"))}
                />
              </Field>
            ) : null}

            {kind === "writing_prompt" ? (
              <Field
                id={id("rubric")}
                label={t("content.editor.rubric")}
                error={error("rubric_id")}
              >
                <select
                  id={id("rubric")}
                  className={FIELD}
                  value={content.rubric_id ?? ""}
                  onChange={(event) => update({ rubric_id: event.target.value || null })}
                  {...invalid(id("rubric"), error("rubric_id"))}
                >
                  <option value="">{t("content.editor.choose")}</option>
                  {(rubrics.data?.items ?? []).map((rubric) => (
                    <option key={rubric.id} value={rubric.id}>
                      {rubric.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : (
              <Field
                id={id("explanation")}
                label={t("content.editor.explanation")}
                error={error("explanation_md")}
              >
                <textarea
                  id={id("explanation")}
                  rows={3}
                  className={FIELD}
                  value={content.explanation_md}
                  onChange={(event) => update({ explanation_md: event.target.value })}
                  {...invalid(id("explanation"), error("explanation_md"))}
                />
              </Field>
            )}

            {current?.open?.state === "in_review" ? (
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={keepInReview}
                    onChange={(event) => setKeepInReview(event.target.checked)}
                  />
                  {t("content.editor.keepInReview")}
                </label>
                <p className="text-sm text-muted-foreground">
                  {t("content.editor.keepInReviewHelp")}
                </p>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="outline" disabled={busy}>
                {t("content.editor.save")}
              </Button>
              <Button type="button" disabled={busy} onClick={() => void save("submit")}>
                {t("content.editor.submit")}
              </Button>
            </div>
          </>
        ) : null}
      </form>

      {module ? <ItemPreview kind={kind} content={shown} context={previewContext} /> : null}

      {conflict ? (
        <EditConflictDialog
          open
          mine={shown}
          current={conflict}
          onKeepMine={() => {
            const latest = conflict.revision;
            setConflict(null);
            setCurrent(conflict);
            setRevision(latest);
            void save("save", latest);
          }}
          onDiscard={() => {
            setConflict(null);
            setCurrent(conflict);
            setRevision(conflict.revision);
            setContent((conflict.open ?? conflict.published)?.content ?? emptyContent());
          }}
        />
      ) : null}
    </div>
  );
}

/** Una versión de solo lectura con su retroalimentación (la publicada, o la abierta sin editor). */
function VersionView({
  item,
  version,
  label,
}: {
  item: Item;
  version: ItemVersion;
  label: string;
}) {
  const { t } = useTranslation();
  return (
    <section aria-label={label} className="space-y-2">
      <h2 className="text-lg font-semibold">
        {label} · {t("content.version", { number: version.number })} ·{" "}
        {t(`content.states.${version.state}`)}
      </h2>
      <ItemPreview kind={item.kind} content={version.content} />
    </section>
  );
}

/**
 * Página de un ítem: el editor (crear en `/banco/items/nuevo`, editar en `/banco/items/$code`) y,
 * para quien revisa, las acciones de revisión (US2).
 */
export function ItemEditorPage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false });
  const code = params.code;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useGetItem(code ?? "", { query: { enabled: Boolean(code) } });
  const refresh = () =>
    code ? void queryClient.invalidateQueries({ queryKey: getGetItemQueryKey(code) }) : undefined;

  if (!code) {
    return (
      <section className="space-y-6">
        <h1 className="text-2xl font-bold">{t("content.editor.newTitle")}</h1>
        <ItemEditor
          onSaved={(saved) =>
            void navigate({ to: "/banco/items/$code", params: { code: saved.code } })
          }
        />
      </section>
    );
  }
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
          <ReviewActions item={item} onChanged={refresh} />
          {item.can.edit ? (
            <ItemEditor key={item.code} item={item} onSaved={refresh} />
          ) : item.open ? (
            <VersionView item={item} version={item.open} label={t("content.openVersion")} />
          ) : null}
          {item.published ? (
            <VersionView
              item={item}
              version={item.published}
              label={t("content.publishedVersion")}
            />
          ) : null}
          {item.kind === "selection" ? <ItemStatistics code={item.code} /> : null}
          <ItemHistory code={item.code} />
        </>
      ) : null}
    </section>
  );
}
