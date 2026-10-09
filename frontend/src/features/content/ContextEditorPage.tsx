import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "@tanstack/react-router";
import { type ReactNode, useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  createContext,
  getGetContextQueryKey,
  updateContext,
  useGetContext,
} from "@/api/content/contexts";
import type {
  Context,
  ContextContent,
  ContextContentKind,
  ModuleCodeValue,
  SharedOption,
} from "@/api/content/model";
import { useListContentModules } from "@/api/content/taxonomy";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { MediaUpload } from "@/features/content/MediaUpload";
import { countWords, validateContext } from "@/features/content/schemas";
import { ApiProblem } from "@/shared/api/http";
import { Button } from "@/shared/ui/button";

const FIELD =
  "mt-1 block w-full rounded-md border border-input bg-background px-3 py-2 text-base aria-[invalid=true]:border-red-600";
const KINDS: ContextContentKind[] = ["text", "table", "image", "shared_options"];

function contentOf(context: Context | undefined): ContextContent {
  if (!context) return { kind: "text", title: "", body_md: "" };
  return {
    kind: context.kind,
    title: context.title,
    body_md: context.body_md ?? null,
    media_id: context.media_id ?? null,
    alt_text: context.alt_text ?? null,
    text_type_node_id: context.text_type_node_id ?? null,
    part_node_id: context.part_node_id ?? null,
    subtype: context.subtype ?? null,
    shared_options: context.shared_options ?? null,
  };
}

/** Deja solo los campos del tipo de contexto y ajusta las opciones a las de la parte. */
function normalized(content: ContextContent, optionCount: number): ContextContent {
  const kind = content.kind;
  const options: SharedOption[] = Array.from({ length: optionCount }, (_, index) => {
    const key = String.fromCharCode(65 + index);
    return content.shared_options?.[index] ?? { key, text: "", feedback: "" };
  });
  return {
    ...content,
    body_md: kind === "text" || kind === "table" ? (content.body_md ?? "") : null,
    media_id: kind === "image" ? (content.media_id ?? null) : null,
    alt_text: kind === "image" ? (content.alt_text ?? "") : null,
    shared_options: kind === "shared_options" ? options : null,
  };
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

function described(id: string, error: string | undefined, extra?: string) {
  const ids = [error ? `${id}-error` : null, extra].filter(Boolean).join(" ");
  return { "aria-invalid": error ? true : undefined, "aria-describedby": ids || undefined };
}

/**
 * Editor de contextos compartidos (US3; FR-005, FR-007, FR-009, FR-020, FR-026). Aplica las
 * reglas del banco antes de guardar y, si el contexto ya lo usan ítems, avisa cuántos y cuántos
 * publicados recibirán una versión nueva En revisión antes de confirmar el cambio.
 */
export function ContextEditor({
  context,
  onSaved,
}: {
  context?: Context;
  onSaved?: (context: Context) => void;
}) {
  const { t } = useTranslation();
  const base = useId();
  const id = (name: string) => `${base}-${name}`;
  const modules = useListContentModules().data?.items ?? [];
  const [moduleCode, setModuleCode] = useState<ModuleCodeValue | "">(context?.module ?? "");
  const module = modules.find((m) => m.code === moduleCode);
  const [code, setCode] = useState(context?.code ?? "");
  const [current, setCurrent] = useState(context);
  const [content, setContent] = useState<ContextContent>(() => contentOf(context));
  const [errors, setErrors] = useState<Map<string, string>>(new Map());
  const [confirming, setConfirming] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [alert, setAlert] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const confirmRef = useRef<HTMLHeadingElement>(null);

  const part = module?.nodes.find((n) => n.id === content.part_node_id && n.kind === "part");
  const optionCount = part?.part_options ?? 4;
  const shown = normalized(content, optionCount);
  const maxWords = module?.max_context_words ?? null;
  const words = shown.body_md != null ? countWords(shown.body_md) : 0;
  const nodes = (kind: "text_type" | "part") =>
    (module?.nodes ?? []).filter((node) => node.kind === kind);
  const error = (field: string) => errors.get(field);

  useEffect(() => {
    if (confirming) confirmRef.current?.focus();
  }, [confirming]);

  function update(patch: Partial<ContextContent>) {
    setContent((previous) => ({ ...previous, ...patch }));
  }

  function setOption(index: number, patch: Partial<SharedOption>) {
    update({
      shared_options: (shown.shared_options ?? []).map((option, i) =>
        i === index ? { ...option, ...patch } : option,
      ),
    });
  }

  function check(): boolean {
    setStatus(null);
    setAlert(null);
    const issues = module ? validateContext(shown, module) : [];
    const map = new Map<string, string>();
    for (const { field, message } of issues) {
      map.set(field, map.has(field) ? `${map.get(field)} ${message}` : message);
    }
    setErrors(map);
    return issues.length === 0;
  }

  async function persist() {
    setConfirming(false);
    setBusy(true);
    try {
      if (!current) {
        if (!module) return;
        const created = await createContext({ ...shown, code, module: module.code });
        setCurrent(created);
        setStatus(t("content.contextEditor.created"));
        onSaved?.(created);
      } else {
        const result = await updateContext(current.code, shown, {
          headers: { "If-Match": `"${current.revision}"` },
        });
        setCurrent(result.context);
        const moved = result.new_review_versions.length
          ? ` ${t("content.contextEditor.movedToReview", { codes: result.new_review_versions.join(", ") })}`
          : "";
        setStatus(
          `${t("content.contextEditor.saved", { version: result.context.version })}${moved}`,
        );
        onSaved?.(result.context);
      }
    } catch (failure) {
      if (failure instanceof ApiProblem && failure.status === 412) {
        const latest = failure.extensions.current as Context | undefined;
        if (latest) {
          setCurrent(latest);
          setContent(contentOf(latest));
        }
        setAlert(t("content.contextEditor.conflict"));
      } else if (failure instanceof ApiProblem && failure.errors?.length) {
        setErrors(new Map(failure.errors.map((e) => [e.field, e.message])));
      } else {
        setAlert(
          failure instanceof ApiProblem && failure.detail ? failure.detail : problemText(failure),
        );
      }
    } finally {
      setBusy(false);
    }
  }

  function save() {
    if (!check()) return;
    if (current && current.item_count > 0) {
      setConfirming(true);
      return;
    }
    void persist();
  }

  const usage = current
    ? current.item_count === 0
      ? t("content.contextEditor.usageNone")
      : `${t("content.contextEditor.usageItems", { count: current.item_count })} ${
          current.published_item_count === 0
            ? t("content.contextEditor.usageNonePublished")
            : t("content.contextEditor.usagePublished", { count: current.published_item_count })
        }`
    : null;

  return (
    <form
      className="max-w-3xl space-y-4"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        save();
      }}
    >
      {status ? (
        <p role="status" aria-live="polite" className="rounded-md bg-muted p-3">
          {status}
        </p>
      ) : null}
      {alert ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {alert}
        </p>
      ) : null}
      {usage ? <p className="text-sm text-muted-foreground">{usage}</p> : null}

      {current ? null : (
        <>
          <Field id={id("module")} label={t("content.editor.module")}>
            <select
              id={id("module")}
              className={FIELD}
              value={moduleCode}
              onChange={(event) => {
                setModuleCode(event.target.value as ModuleCodeValue);
                update({ text_type_node_id: null, part_node_id: null });
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
              {...described(id("code"), error("code"))}
            />
          </Field>
        </>
      )}

      {module ? (
        <>
          <Field id={id("kind")} label={t("content.contextEditor.kind")}>
            <select
              id={id("kind")}
              className={FIELD}
              value={content.kind}
              disabled={Boolean(current)}
              onChange={(event) => update({ kind: event.target.value as ContextContentKind })}
            >
              {KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`content.contextEditor.kinds.${kind}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field id={id("title")} label={t("content.contextEditor.title")} error={error("title")}>
            <input
              id={id("title")}
              className={FIELD}
              value={content.title}
              onChange={(event) => update({ title: event.target.value })}
              {...described(id("title"), error("title"))}
            />
          </Field>

          {nodes("text_type").length ? (
            <Field
              id={id("text-type")}
              label={t("content.contextEditor.textType")}
              error={error("text_type_node_id")}
            >
              <select
                id={id("text-type")}
                className={FIELD}
                value={content.text_type_node_id ?? ""}
                onChange={(event) => update({ text_type_node_id: event.target.value || null })}
                {...described(id("text-type"), error("text_type_node_id"))}
              >
                <option value="">{t("content.editor.choose")}</option>
                {nodes("text_type").map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.code} · {node.name}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          {nodes("part").length ? (
            <Field
              id={id("part")}
              label={t("content.contextEditor.part")}
              error={error("part_node_id")}
            >
              <select
                id={id("part")}
                className={FIELD}
                value={content.part_node_id ?? ""}
                onChange={(event) => update({ part_node_id: event.target.value || null })}
                {...described(id("part"), error("part_node_id"))}
              >
                <option value="">{t("content.editor.choose")}</option>
                {nodes("part").map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.code} · {node.name}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}

          {content.kind === "text" || content.kind === "table" ? (
            <Field
              id={id("body")}
              label={t(`content.contextEditor.${content.kind === "text" ? "body" : "table"}`)}
              error={error("body_md")}
            >
              <textarea
                id={id("body")}
                rows={10}
                className={FIELD}
                value={shown.body_md ?? ""}
                onChange={(event) => update({ body_md: event.target.value })}
                {...described(id("body"), error("body_md"), id("words"))}
              />
              <p
                id={id("words")}
                className={
                  maxWords != null && words > maxWords
                    ? "mt-1 text-sm font-semibold text-red-700"
                    : "mt-1 text-sm text-muted-foreground"
                }
              >
                {maxWords != null
                  ? t("content.contextEditor.words", { count: words, max: maxWords })
                  : t("content.contextEditor.wordsNoMax", { count: words })}
              </p>
            </Field>
          ) : null}

          {content.kind === "image" ? (
            <>
              <MediaUpload
                mediaId={content.media_id}
                onUploaded={(media) => update({ media_id: media.id })}
                describedBy={error("media_id") ? `${id("media")}-error` : undefined}
              />
              {error("media_id") ? (
                <p id={`${id("media")}-error`} className="text-sm text-red-700">
                  {error("media_id")}
                </p>
              ) : null}
              <Field
                id={id("alt")}
                label={t("content.contextEditor.altText")}
                error={error("alt_text")}
              >
                <textarea
                  id={id("alt")}
                  rows={3}
                  className={FIELD}
                  value={content.alt_text ?? ""}
                  onChange={(event) => update({ alt_text: event.target.value })}
                  {...described(id("alt"), error("alt_text"))}
                />
              </Field>
            </>
          ) : null}

          {content.kind === "shared_options" ? (
            <fieldset
              className="space-y-3 rounded-md border p-3"
              aria-describedby={error("shared_options") ? `${id("shared")}-error` : undefined}
            >
              <legend className="font-medium">{t("content.contextEditor.sharedOptions")}</legend>
              {error("shared_options") ? (
                <p id={`${id("shared")}-error`} className="text-sm text-red-700">
                  {error("shared_options")}
                </p>
              ) : null}
              {(shown.shared_options ?? []).map((option, index) => {
                const text = `shared_options[${option.key}].text`;
                const feedback = `shared_options[${option.key}].feedback`;
                return (
                  <div
                    key={option.key}
                    className="grid gap-2 border-t pt-3 first:border-t-0 md:grid-cols-2"
                  >
                    <Field
                      id={id(`option-${option.key}`)}
                      label={t("content.editor.optionText", { key: option.key })}
                      error={error(text)}
                    >
                      <input
                        id={id(`option-${option.key}`)}
                        className={FIELD}
                        value={option.text}
                        onChange={(event) => setOption(index, { text: event.target.value })}
                        {...described(id(`option-${option.key}`), error(text))}
                      />
                    </Field>
                    <Field
                      id={id(`feedback-${option.key}`)}
                      label={t("content.editor.optionFeedback", { key: option.key })}
                      error={error(feedback)}
                    >
                      <input
                        id={id(`feedback-${option.key}`)}
                        className={FIELD}
                        value={option.feedback}
                        onChange={(event) => setOption(index, { feedback: event.target.value })}
                        {...described(id(`feedback-${option.key}`), error(feedback))}
                      />
                    </Field>
                  </div>
                );
              })}
            </fieldset>
          ) : null}

          <Button type="submit" disabled={busy}>
            {t(current ? "content.contextEditor.save" : "content.contextEditor.create")}
          </Button>
        </>
      ) : null}

      {confirming ? (
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby={id("confirm-title")}
          aria-describedby={id("confirm-usage")}
          className="rounded-md border border-amber-300 bg-amber-50 p-4"
        >
          <h2 id={id("confirm-title")} ref={confirmRef} tabIndex={-1} className="font-semibold">
            {t("content.contextEditor.confirmTitle")}
          </h2>
          <p id={id("confirm-usage")}>{usage}</p>
          <div className="mt-3 flex gap-2">
            <Button type="button" onClick={() => void persist()}>
              {t("content.contextEditor.confirm")}
            </Button>
            <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
              {t("content.contextEditor.cancel")}
            </Button>
          </div>
        </div>
      ) : null}
    </form>
  );
}

/**
 * Página de un contexto: crear en `/banco/contextos/nuevo` o editar en `/banco/contextos/$code`.
 */
export function ContextEditorPage() {
  const { t } = useTranslation();
  const params = useParams({ strict: false });
  const code = params.code === "nuevo" ? undefined : params.code;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useGetContext(code ?? "", { query: { enabled: Boolean(code) } });

  if (!code) {
    return (
      <section className="space-y-6">
        <h1 className="text-2xl font-bold">{t("content.contextEditor.newTitle")}</h1>
        <ContextEditor
          onSaved={(saved) =>
            void navigate({ to: "/banco/contextos/$code", params: { code: saved.code } })
          }
        />
      </section>
    );
  }
  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">
        {t("content.pages.context")} {code}
      </h1>
      <ReauthAlert error={query.error} returnTo={`/banco/contextos/${code}`} />
      {query.isError && !isReauth(query.error) ? (
        <p role="alert">{problemText(query.error)}</p>
      ) : null}
      {query.data ? (
        <ContextEditor
          key={query.data.code}
          context={query.data}
          onSaved={() =>
            void queryClient.invalidateQueries({ queryKey: getGetContextQueryKey(code) })
          }
        />
      ) : null}
    </section>
  );
}
