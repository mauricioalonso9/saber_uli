import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ContentModule, Rubric, RubricInput, TaxonomyNode } from "@/api/content/model";
import {
  createRubric,
  createTaxonomyNode,
  deleteTaxonomyNode,
  getListContentModulesQueryKey,
  getListRubricsQueryKey,
  updateContentModule,
  updateRubric,
  updateTaxonomyNode,
  useListContentModules,
  useListRubrics,
} from "@/api/content/taxonomy";
import { isReauth, problemText, ReauthAlert } from "@/features/admin/common";
import { Button } from "@/shared/ui/button";

const INPUT = "mt-1 block w-full rounded-md border border-input bg-background px-3 py-2";
const PARENT: Partial<Record<TaxonomyNode["kind"], TaxonomyNode["kind"]>> = {
  assertion: "competence",
  evidence: "assertion",
};
const KINDS: TaxonomyNode["kind"][] = [
  "competence",
  "assertion",
  "evidence",
  "component",
  "situation",
  "text_type",
  "part",
];

type Notice = { kind: "status"; text: string } | { kind: "error"; error: unknown } | null;

/** "0,3" o "0.3" → 0.3; vacío → null; otra cosa → undefined (inválido). */
function parseWeight(text: string): number | null | undefined {
  const clean = text.trim().replace(",", ".");
  if (!clean) return null;
  const value = Number(clean);
  return Number.isFinite(value) && value >= 0 && value <= 1 ? value : undefined;
}

function NodeEntry({
  node,
  childrenOf,
  onDone,
}: {
  node: TaxonomyNode;
  childrenOf: (id: string) => TaxonomyNode[];
  onDone: (notice: Notice) => void;
}) {
  const { t } = useTranslation();
  const labelId = useId();
  const weightId = useId();
  const [weight, setWeight] = useState(
    node.target_weight == null ? "" : String(node.target_weight).replace(".", ","),
  );
  const nested = childrenOf(node.id);

  async function run(action: () => Promise<string>) {
    try {
      onDone({ kind: "status", text: await action() });
    } catch (error) {
      onDone({ kind: "error", error });
    }
  }

  function saveWeight() {
    const value = parseWeight(weight);
    if (value === undefined) {
      onDone({ kind: "status", text: t("content.taxonomy.invalidWeight") });
      return;
    }
    void run(async () => {
      const saved = await updateTaxonomyNode(node.id, { target_weight: value });
      return saved.warnings?.length
        ? saved.warnings.join(" ")
        : t("content.taxonomy.saved", { code: node.code });
    });
  }

  return (
    <li aria-labelledby={labelId} className="space-y-2 rounded-md border p-3">
      <p>
        <span id={labelId} className="font-medium">
          <span className="font-mono">{node.code}</span> · {node.name}
        </span>{" "}
        <span className="text-sm text-muted-foreground">
          {t(`content.taxonomy.kinds.${node.kind}`)}
          {node.active ? "" : ` · ${t("content.taxonomy.inactive")}`}
          {node.in_use ? ` · ${t("content.taxonomy.inUse")}` : ""}
        </span>
      </p>
      <div className="flex flex-wrap items-end gap-2">
        {node.kind !== "evidence" ? (
          <>
            <div>
              <label htmlFor={weightId} className="text-sm">
                {t("content.taxonomy.weightOf", { code: node.code })}
              </label>
              <input
                id={weightId}
                inputMode="decimal"
                className={`${INPUT} w-28`}
                value={weight}
                onChange={(event) => setWeight(event.target.value)}
              />
            </div>
            <Button type="button" variant="outline" onClick={saveWeight}>
              {t("content.taxonomy.save", { code: node.code })}
            </Button>
          </>
        ) : null}
        {node.active ? (
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              void run(async () => {
                await updateTaxonomyNode(node.id, { active: false });
                return t("content.taxonomy.deactivated", { code: node.code });
              })
            }
          >
            {t("content.taxonomy.deactivate", { code: node.code })}
          </Button>
        ) : (
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              void run(async () => {
                await updateTaxonomyNode(node.id, { active: true });
                return t("content.taxonomy.reactivated", { code: node.code });
              })
            }
          >
            {t("content.taxonomy.reactivate", { code: node.code })}
          </Button>
        )}
        {!node.in_use ? (
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              void run(async () => {
                await deleteTaxonomyNode(node.id);
                return t("content.taxonomy.deleted", { code: node.code });
              })
            }
          >
            {t("content.taxonomy.delete", { code: node.code })}
          </Button>
        ) : null}
      </div>
      {nested.length ? (
        <ul className="space-y-2 pl-4">
          {nested.map((child) => (
            <NodeEntry key={child.id} node={child} childrenOf={childrenOf} onDone={onDone} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function Tree({ module, onDone }: { module: ContentModule; onDone: (notice: Notice) => void }) {
  const { t } = useTranslation();
  const childrenOf = (id: string) => module.nodes.filter((n) => n.parent_id === id);
  const roots = module.nodes.filter((n) => !n.parent_id);
  return (
    <ul
      aria-label={t("content.taxonomy.tree", { module: t(`content.modules.${module.code}`) })}
      className="space-y-2"
    >
      {roots.map((root) => (
        <NodeEntry key={root.id} node={root} childrenOf={childrenOf} onDone={onDone} />
      ))}
    </ul>
  );
}

function NewNodeForm({ module, onDone }: { module: ContentModule; onDone: (n: Notice) => void }) {
  const { t } = useTranslation();
  const id = useId();
  const [kind, setKind] = useState<TaxonomyNode["kind"]>("competence");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [weight, setWeight] = useState("");
  const parentKind = PARENT[kind];
  const parents = parentKind ? module.nodes.filter((n) => n.kind === parentKind && n.active) : [];

  async function submit() {
    const value = parseWeight(weight);
    if (value === undefined) {
      onDone({ kind: "status", text: t("content.taxonomy.invalidWeight") });
      return;
    }
    try {
      const created = await createTaxonomyNode({
        module: module.code,
        kind,
        code: code.trim(),
        name: name.trim(),
        ...(parentKind && parent ? { parent_id: parent } : {}),
        ...(value != null ? { target_weight: value } : {}),
      });
      setCode("");
      setName("");
      setWeight("");
      onDone({
        kind: "status",
        text: [
          t("content.taxonomy.created", { code: created.code }),
          ...(created.warnings ?? []),
        ].join(" "),
      });
    } catch (error) {
      onDone({ kind: "error", error });
    }
  }

  return (
    <form
      aria-label={t("content.taxonomy.newNode")}
      className="grid gap-3 rounded-md border p-4 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <h2 className="font-medium sm:col-span-2">{t("content.taxonomy.newNode")}</h2>
      <div>
        <label htmlFor={`${id}-kind`}>{t("content.taxonomy.kind")}</label>
        <select
          id={`${id}-kind`}
          className={INPUT}
          value={kind}
          onChange={(event) => setKind(event.target.value as TaxonomyNode["kind"])}
        >
          {KINDS.filter((k) => k !== "part").map((k) => (
            <option key={k} value={k}>
              {t(`content.taxonomy.kinds.${k}`)}
            </option>
          ))}
        </select>
      </div>
      {parentKind ? (
        <div>
          <label htmlFor={`${id}-parent`}>{t("content.taxonomy.parent")}</label>
          <select
            id={`${id}-parent`}
            className={INPUT}
            value={parent}
            required
            onChange={(event) => setParent(event.target.value)}
          >
            <option value="">{t("content.editor.choose")}</option>
            {parents.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} · {p.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      <div>
        <label htmlFor={`${id}-code`}>{t("content.taxonomy.nodeCode")}</label>
        <input
          id={`${id}-code`}
          className={INPUT}
          required
          value={code}
          onChange={(event) => setCode(event.target.value.toUpperCase())}
        />
      </div>
      <div>
        <label htmlFor={`${id}-name`}>{t("content.taxonomy.nodeName")}</label>
        <input
          id={`${id}-name`}
          className={INPUT}
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <div>
        <label htmlFor={`${id}-weight`}>{t("content.taxonomy.weight")}</label>
        <input
          id={`${id}-weight`}
          inputMode="decimal"
          className={INPUT}
          value={weight}
          onChange={(event) => setWeight(event.target.value)}
        />
      </div>
      <div className="sm:col-span-2">
        <Button type="submit">{t("content.taxonomy.add")}</Button>
      </div>
    </form>
  );
}

interface DimensionDraft {
  code: string;
  name: string;
  levels: string;
}

function emptyRubric(): RubricInput {
  return {
    code: "",
    name: "",
    note: null,
    active: true,
    relevance_condition: { name: "", description: "" },
    dimensions: [],
  };
}

function RubricForm({
  rubric,
  onDone,
}: {
  rubric: Rubric | null;
  onDone: (notice: Notice, saved?: boolean) => void;
}) {
  const { t } = useTranslation();
  const id = useId();
  const start = rubric ?? emptyRubric();
  const [code, setCode] = useState(start.code);
  const [name, setName] = useState(start.name);
  const [note, setNote] = useState(start.note ?? "");
  const [active, setActive] = useState(start.active);
  const [condition, setCondition] = useState(start.relevance_condition);
  const [dimensions, setDimensions] = useState<DimensionDraft[]>(
    start.dimensions.length
      ? start.dimensions.map((d) => ({
          code: d.code,
          name: d.name,
          levels: d.levels.map((level) => level.description).join("\n"),
        }))
      : [{ code: "", name: "", levels: "" }],
  );

  function setDimension(index: number, change: Partial<DimensionDraft>) {
    setDimensions((all) => all.map((d, i) => (i === index ? { ...d, ...change } : d)));
  }

  async function submit() {
    const body: RubricInput = {
      code: code.trim(),
      name: name.trim(),
      note: note.trim() || null,
      active,
      relevance_condition: {
        name: condition.name.trim(),
        description: condition.description.trim(),
      },
      dimensions: dimensions.map((d) => ({
        code: d.code.trim(),
        name: d.name.trim(),
        levels: d.levels
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean)
          .map((description, index) => ({ level: index + 1, description })),
      })),
    };
    try {
      const saved = rubric ? await updateRubric(rubric.id, body) : await createRubric(body);
      onDone(
        { kind: "status", text: t("content.taxonomy.rubricSaved", { code: saved.code }) },
        true,
      );
    } catch (error) {
      onDone({ kind: "error", error });
    }
  }

  const field = (key: string, label: string, value: string, set: (v: string) => void) => (
    <div>
      <label htmlFor={`${id}-${key}`}>{label}</label>
      <input
        id={`${id}-${key}`}
        className={INPUT}
        value={value}
        onChange={(event) => set(event.target.value)}
      />
    </div>
  );

  return (
    <form
      aria-label={t("content.taxonomy.rubric")}
      className="space-y-3 rounded-md border p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {field("code", t("content.taxonomy.rubricCode"), code, (v) => setCode(v.toUpperCase()))}
        {field("name", t("content.taxonomy.rubricName"), name, setName)}
        {field("condition", t("content.taxonomy.condition"), condition.name, (v) =>
          setCondition({ ...condition, name: v }),
        )}
        {field("requires", t("content.taxonomy.conditionText"), condition.description, (v) =>
          setCondition({ ...condition, description: v }),
        )}
        {field("note", t("content.taxonomy.note"), note, setNote)}
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
          />
          {t("content.taxonomy.rubricActive")}
        </label>
      </div>
      {dimensions.map((dimension, index) => {
        const number = index + 1;
        return (
          <fieldset key={index} className="space-y-2 rounded-md border p-3">
            <legend className="font-medium">{t("content.taxonomy.dimension", { number })}</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {field(
                `dim-${index}-code`,
                t("content.taxonomy.dimensionCode", { number }),
                dimension.code,
                (v) => setDimension(index, { code: v }),
              )}
              {field(
                `dim-${index}-name`,
                t("content.taxonomy.dimensionName", { number }),
                dimension.name,
                (v) => setDimension(index, { name: v }),
              )}
            </div>
            <label htmlFor={`${id}-dim-${index}-levels`}>
              {t("content.taxonomy.levels", { number })}
            </label>
            <textarea
              id={`${id}-dim-${index}-levels`}
              className={INPUT}
              rows={3}
              value={dimension.levels}
              onChange={(event) => setDimension(index, { levels: event.target.value })}
            />
            {dimensions.length > 1 ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => setDimensions((all) => all.filter((_, i) => i !== index))}
              >
                {t("content.taxonomy.removeDimension", { number })}
              </Button>
            ) : null}
          </fieldset>
        );
      })}
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => setDimensions((all) => [...all, { code: "", name: "", levels: "" }])}
        >
          {t("content.taxonomy.addDimension")}
        </Button>
        <Button type="submit">{t("content.taxonomy.saveRubric")}</Button>
      </div>
    </form>
  );
}

/**
 * Mantenimiento de la taxonomía (US9; FR-001, FR-040, FR-045): categorías por módulo con su peso
 * objetivo, la meta del módulo y las rúbricas. Lo que está en uso solo se desactiva.
 */
export function TaxonomyPage() {
  const { t } = useTranslation();
  const ids = { module: useId(), target: useId() };
  const queryClient = useQueryClient();
  const modules = useListContentModules({ include_inactive: true });
  const rubrics = useListRubrics();
  const [code, setCode] = useState<string | null>(null);
  const [target, setTarget] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [editing, setEditing] = useState<Rubric | "new" | null>(null);
  const items = modules.data?.items ?? [];
  const module = items.find((m) => m.code === code) ?? items[0];

  function done(next: Notice, closeRubric = false) {
    setNotice(next);
    if (next?.kind === "status") {
      void queryClient.invalidateQueries({ queryKey: getListContentModulesQueryKey() });
      void queryClient.invalidateQueries({ queryKey: getListRubricsQueryKey() });
      if (closeRubric) setEditing(null);
    }
  }

  async function saveTarget() {
    if (!module) return;
    const value = Number(target ?? module.bank_target);
    try {
      await updateContentModule(module.code, { bank_target: value });
      setTarget(null);
      done({ kind: "status", text: t("content.taxonomy.targetSaved") });
    } catch (error) {
      done({ kind: "error", error });
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">{t("content.pages.taxonomy")}</h1>
      <ReauthAlert error={modules.error} returnTo="/admin/taxonomia" />
      {notice?.kind === "status" ? (
        <p role="status" className="rounded-md border border-green-300 bg-green-50 p-3">
          {notice.text}
        </p>
      ) : null}
      {notice?.kind === "error" && !isReauth(notice.error) ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {problemText(notice.error)}
        </p>
      ) : null}

      {module ? (
        <>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label htmlFor={ids.module} className="font-medium">
                {t("content.fields.module")}
              </label>
              <select
                id={ids.module}
                className={INPUT}
                value={module.code}
                onChange={(event) => {
                  setCode(event.target.value);
                  setTarget(null);
                }}
              >
                {items.map((m) => (
                  <option key={m.code} value={m.code}>
                    {t(`content.modules.${m.code}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor={ids.target} className="font-medium">
                {t("content.taxonomy.target")}
              </label>
              <input
                id={ids.target}
                type="number"
                min={1}
                max={10000}
                className={`${INPUT} w-32`}
                value={target ?? module.bank_target}
                onChange={(event) => setTarget(event.target.value)}
              />
            </div>
            <Button type="button" onClick={() => void saveTarget()}>
              {t("content.taxonomy.saveTarget")}
            </Button>
          </div>
          <Tree key={module.code} module={module} onDone={done} />
          <NewNodeForm key={`new-${module.code}`} module={module} onDone={done} />
        </>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">{t("content.taxonomy.rubrics")}</h2>
        <ul className="space-y-1">
          {(rubrics.data?.items ?? []).map((rubric) => (
            <li key={rubric.id} className="flex flex-wrap items-center gap-2">
              <span className="font-mono">{rubric.code}</span> · {rubric.name}
              {rubric.active ? "" : ` · ${t("content.taxonomy.inactive")}`}
              <Button type="button" variant="outline" onClick={() => setEditing(rubric)}>
                {t("content.taxonomy.editRubric", { code: rubric.code })}
              </Button>
            </li>
          ))}
        </ul>
        {editing ? (
          <RubricForm
            key={editing === "new" ? "new" : editing.id}
            rubric={editing === "new" ? null : editing}
            onDone={done}
          />
        ) : (
          <Button type="button" variant="outline" onClick={() => setEditing("new")}>
            {t("content.taxonomy.newRubric")}
          </Button>
        )}
      </section>
    </section>
  );
}
