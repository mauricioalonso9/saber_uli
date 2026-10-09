/**
 * Reglas del banco en el editor (FR-024): las mismas del servidor (`content/domain/item_version.py`,
 * `context.py`, `module.py` y `word_count.py`), con los mismos `field` y `rule` de `errors[]`, para
 * mostrar cada error junto a su campo antes de guardar o enviar. El servidor sigue siendo quien
 * decide; si una regla cambia allá, cambia aquí.
 *
 * Todo sale de los datos del módulo (`listContentModules`): qué categorías son obligatorias,
 * cuántas opciones lleva un ítem o una parte de Inglés y cuál es el máximo de palabras.
 */
import { z } from "zod";
import type {
  ContentModule,
  ContextContent,
  ItemContent,
  ItemKind,
  TaxonomyNode,
  TaxonomyTags,
} from "@/api/content/model";

export const ValidationRule = {
  required: "required",
  invalid_value: "invalid_value",
  single_correct_option: "single_correct_option",
  option_count: "option_count",
  option_feedback_required: "option_feedback_required",
  explanation_required: "explanation_required",
  taxonomy_unknown: "taxonomy_unknown",
  taxonomy_inactive: "taxonomy_inactive",
  taxonomy_mismatch: "taxonomy_mismatch",
  context_unknown: "context_unknown",
  context_word_limit: "context_word_limit",
  alt_text_required: "alt_text_required",
  matching_key_unknown: "matching_key_unknown",
  rubric_unknown: "rubric_unknown",
} as const;
export type ValidationRule = (typeof ValidationRule)[keyof typeof ValidationRule];

export interface ContentIssue {
  /** Como en el servidor: `stem_md`, `options[B].feedback`, `taxonomy.assertion_id`… */
  field: string;
  rule: ValidationRule;
  message: string;
}

export const MAX_MATCHING_ITEMS_PER_CONTEXT = 5;

// --------------------------------------------------------------------- palabras (R-10)

const LINK_TARGET = /(!?\[[^\]]*\])\([^)]*\)/g;
const ORDERED_MARKER = /^\s*\d+[.)]\s+/gm;
const WORD = /[\p{L}\p{N}]+(?:[-'’.,][\p{L}\p{N}]+)*/gu;

/** Palabras que lee el estudiante: sin URL de enlaces ni marcas de listas o tablas. */
export function countWords(markdown: string): number {
  const text = markdown.replace(LINK_TARGET, "$1").replace(ORDERED_MARKER, "");
  return text.match(WORD)?.length ?? 0;
}

// --------------------------------------------------------------------- módulo

const TAG_KINDS = [
  "competence",
  "assertion",
  "evidence",
  "component",
  "situation",
  "part",
] as const;
type TagKind = (typeof TAG_KINDS)[number];
const PARENT_KIND: Partial<Record<TagKind, TagKind>> = {
  assertion: "competence",
  evidence: "assertion",
};
const KIND_NAMES: Record<TagKind, string> = {
  competence: "la competencia",
  assertion: "la afirmación",
  evidence: "la evidencia",
  component: "el componente",
  situation: "el tipo de situación",
  part: "la parte",
};

class ModuleRules {
  private readonly nodes: Map<string, TaxonomyNode>;
  readonly requiredTags: Set<TagKind>;

  constructor(
    readonly module: ContentModule,
    private readonly rubricIds?: ReadonlySet<string>,
  ) {
    this.nodes = new Map(
      module.nodes.filter((n) => n.module === module.code).map((n) => [n.id, n]),
    );
    const present = new Set(module.nodes.map((n) => n.kind));
    this.requiredTags = new Set(TAG_KINDS.filter((kind) => present.has(kind)));
  }

  node(id: string | null | undefined): TaxonomyNode | undefined {
    return id ? this.nodes.get(id) : undefined;
  }

  hasKind(kind: TaxonomyNode["kind"]): boolean {
    return [...this.nodes.values()].some((n) => n.kind === kind);
  }

  optionCount(partId: string | null | undefined): number | null {
    const part = this.node(partId);
    if (part?.kind === "part") return part.part_options ?? null;
    return this.module.options_per_item ?? null;
  }

  partFormat(partId: string | null | undefined): string | null {
    const part = this.node(partId);
    return part?.kind === "part" ? (part.part_format ?? null) : null;
  }

  /** `undefined` si no se conocen las rúbricas: entonces solo se exige elegir una. */
  hasRubric(id: string): boolean | undefined {
    return this.rubricIds?.has(id);
  }

  checkTags(tags: TaxonomyTags, alreadyUsed: ReadonlySet<string>): ContentIssue[] {
    const issues: ContentIssue[] = [];
    const name = (kind: TagKind) => KIND_NAMES[kind];
    const capital = (kind: TagKind) => name(kind).charAt(0).toUpperCase() + name(kind).slice(1);
    for (const kind of TAG_KINDS) {
      const field = `taxonomy.${kind}_id`;
      const id = tags[`${kind}_id`];
      if (!id) {
        if (this.requiredTags.has(kind))
          issues.push(issue(field, "required", `Falta ${name(kind)}.`));
        continue;
      }
      const node = this.node(id);
      if (!node) {
        issues.push(
          issue(field, "taxonomy_unknown", `${capital(kind)} no existe en ${this.module.name}.`),
        );
      } else if (node.kind !== kind) {
        issues.push(
          issue(field, "taxonomy_mismatch", `El código ${node.code} no es ${name(kind)}.`),
        );
      } else if (!node.active && !alreadyUsed.has(id)) {
        issues.push(
          issue(field, "taxonomy_inactive", `${capital(kind)} ${node.code} está desactivada.`),
        );
      } else {
        const parentKind = PARENT_KIND[kind];
        const parentId = parentKind ? tags[`${parentKind}_id`] : null;
        if (parentKind && parentId && node.parent_id !== parentId) {
          issues.push(
            issue(
              field,
              "taxonomy_mismatch",
              `${capital(kind)} ${node.code} no pertenece a ${name(parentKind)} elegida.`,
            ),
          );
        }
      }
    }
    return issues;
  }
}

function issue(field: string, rule: ValidationRule, message: string): ContentIssue {
  return { field, rule, message };
}

const blank = (value: string | null | undefined) => !value || !value.trim();

const keysInOrder = (keys: string[]) =>
  keys.every((key, index) => key === String.fromCharCode(65 + index));

// --------------------------------------------------------------------- forma (contrato)

const uuidOrNull = z.string().nullable().optional();

const optionShape = z.object({
  key: z.string().regex(/^[A-D]$/),
  text: z.string().max(2000),
  correct: z.boolean(),
  feedback: z.string().max(2000),
});

const itemShape = z.object({
  difficulty: z.enum(["low", "medium", "high"]),
  context_code: z.string().max(32).nullable().optional(),
  taxonomy: z.object({
    competence_id: uuidOrNull,
    assertion_id: uuidOrNull,
    evidence_id: uuidOrNull,
    component_id: uuidOrNull,
    situation_id: uuidOrNull,
    part_id: uuidOrNull,
  }),
  stem_md: z.string().max(5000),
  options: z.array(optionShape).max(4).nullable().optional(),
  answer_key: z
    .string()
    .regex(/^[A-H]$/)
    .nullable()
    .optional(),
  explanation_md: z.string().max(5000),
  prompt_context_md: z.string().max(5000).nullable().optional(),
  rubric_id: uuidOrNull,
});

const contextShape = z.object({
  kind: z.enum(["text", "table", "image", "shared_options"]),
  title: z.string().max(200),
  body_md: z.string().max(20000).nullable().optional(),
  media_id: uuidOrNull,
  alt_text: z.string().max(1000).nullable().optional(),
  text_type_node_id: uuidOrNull,
  part_node_id: uuidOrNull,
  subtype: z.string().max(60).nullable().optional(),
  shared_options: z
    .array(
      z.object({
        key: z.string().regex(/^[A-H]$/),
        text: z.string().max(500),
        feedback: z.string().max(2000),
      }),
    )
    .max(8)
    .nullable()
    .optional(),
});

// --------------------------------------------------------------------- reglas del ítem

export interface ItemRuleOptions {
  /** Versión vigente del contexto elegido; `null` si el código no existe. */
  context?: ContextContent | null;
  /** Otros ítems de emparejamiento que ya usan el contexto. */
  matchingSiblings?: number;
  /** Categorías que el ítem ya tenía: siguen válidas aunque estén desactivadas. */
  alreadyUsed?: ReadonlySet<string>;
  /** Rúbricas existentes; sin ellas solo se exige elegir una. */
  rubricIds?: ReadonlySet<string>;
}

function itemIssues(
  kind: ItemKind,
  content: ItemContent,
  rules: ModuleRules,
  options: ItemRuleOptions,
): ContentIssue[] {
  const issues: ContentIssue[] = [];
  const writingModule = rules.module.question_type === "writing";
  if (writingModule !== (kind === "writing_prompt")) {
    issues.push(
      issue("kind", "taxonomy_mismatch", `El tipo no corresponde a ${rules.module.name}.`),
    );
  }
  if (blank(content.stem_md)) issues.push(issue("stem_md", "required", "Escribe el enunciado."));
  if (kind !== "writing_prompt" && blank(content.explanation_md)) {
    issues.push(issue("explanation_md", "explanation_required", "Escribe la explicación general."));
  }
  const context = options.context;
  if (content.context_code && context === null) {
    issues.push(issue("context_code", "context_unknown", "El contexto indicado no existe."));
  }
  issues.push(...rules.checkTags(content.taxonomy, options.alreadyUsed ?? new Set()));
  const partId = content.taxonomy.part_id;
  const partFormat = rules.partFormat(partId);
  if (kind === "selection") {
    if (partFormat === "matching") {
      issues.push(
        issue(
          "taxonomy.part_id",
          "taxonomy_mismatch",
          "Esta parte es de emparejamiento: el ítem debe usar las opciones del contexto.",
        ),
      );
    }
    issues.push(...selectionIssues(content, rules));
  } else if (kind === "matching") {
    issues.push(...matchingIssues(content, partFormat, context, options.matchingSiblings ?? 0));
  } else {
    issues.push(...writingIssues(content, rules));
  }
  return issues;
}

function selectionIssues(content: ItemContent, rules: ModuleRules): ContentIssue[] {
  const issues: ContentIssue[] = [];
  const options = content.options ?? [];
  const expected = rules.optionCount(content.taxonomy.part_id);
  if (
    (expected !== null && options.length !== expected) ||
    !keysInOrder(options.map((o) => o.key))
  ) {
    issues.push(
      issue(
        "options",
        "option_count",
        `El ítem debe tener ${expected} opciones con claves desde la A, en orden.`,
      ),
    );
  }
  if (options.filter((o) => o.correct).length !== 1) {
    issues.push(
      issue("options", "single_correct_option", "Marca exactamente una opción correcta."),
    );
  }
  for (const option of options) {
    if (blank(option.text))
      issues.push(issue(`options[${option.key}].text`, "required", "Escribe la opción."));
    if (blank(option.feedback)) {
      issues.push(
        issue(
          `options[${option.key}].feedback`,
          "option_feedback_required",
          `La opción ${option.key} necesita su retroalimentación.`,
        ),
      );
    }
  }
  return issues;
}

function matchingIssues(
  content: ItemContent,
  partFormat: string | null,
  context: ContextContent | null | undefined,
  siblings: number,
): ContentIssue[] {
  const issues: ContentIssue[] = [];
  if (content.options?.length) {
    issues.push(
      issue("options", "option_count", "El emparejamiento usa las opciones del contexto."),
    );
  }
  if (content.taxonomy.part_id && partFormat !== "matching") {
    issues.push(
      issue("taxonomy.part_id", "taxonomy_mismatch", "La parte no es de emparejamiento."),
    );
  }
  if (!content.context_code) {
    issues.push(issue("context_code", "required", "Elige el contexto con las opciones."));
  } else if (context && context.kind !== "shared_options") {
    issues.push(
      issue("context_code", "taxonomy_mismatch", "El contexto no tiene opciones compartidas."),
    );
  }
  if (siblings >= MAX_MATCHING_ITEMS_PER_CONTEXT) {
    issues.push(
      issue(
        "context_code",
        "option_count",
        `Un contexto admite como máximo ${MAX_MATCHING_ITEMS_PER_CONTEXT} descripciones.`,
      ),
    );
  }
  if (blank(content.answer_key)) {
    issues.push(issue("answer_key", "required", "Elige la respuesta correcta."));
  } else if (context && !(context.shared_options ?? []).some((o) => o.key === content.answer_key)) {
    issues.push(
      issue(
        "answer_key",
        "matching_key_unknown",
        "La respuesta no está entre las opciones del contexto.",
      ),
    );
  }
  return issues;
}

function writingIssues(content: ItemContent, rules: ModuleRules): ContentIssue[] {
  const issues: ContentIssue[] = [];
  if (content.options?.length)
    issues.push(issue("options", "option_count", "Una consigna no lleva opciones."));
  if (blank(content.prompt_context_md)) {
    issues.push(issue("prompt_context_md", "required", "Escribe el contexto de la consigna."));
  }
  if (!content.rubric_id) {
    issues.push(issue("rubric_id", "required", "Elige la rúbrica."));
  } else if (rules.hasRubric(content.rubric_id) === false) {
    issues.push(issue("rubric_id", "rubric_unknown", "La rúbrica no existe."));
  }
  return issues;
}

// --------------------------------------------------------------------- reglas del contexto

function contextIssues(content: ContextContent, rules: ModuleRules): ContentIssue[] {
  const issues: ContentIssue[] = [];
  if (blank(content.title))
    issues.push(issue("title", "required", "Escribe el título del contexto."));
  if ((content.kind === "text" || content.kind === "table") && blank(content.body_md)) {
    issues.push(issue("body_md", "required", "Escribe el texto del contexto."));
  }
  if (content.kind === "image") {
    if (!content.media_id)
      issues.push(issue("media_id", "required", "Sube la imagen del contexto."));
    if (blank(content.alt_text)) {
      issues.push(
        issue(
          "alt_text",
          "alt_text_required",
          "Describe la imagen para quienes usan lector de pantalla.",
        ),
      );
    }
  }
  if (content.kind === "shared_options") issues.push(...sharedOptionIssues(content, rules));
  const limit = rules.module.max_context_words;
  if (limit != null && content.body_md != null) {
    const words = countWords(content.body_md);
    if (words > limit) {
      issues.push(
        issue(
          "body_md",
          "context_word_limit",
          `El texto tiene ${words}/${limit} palabras; el máximo es ${limit}.`,
        ),
      );
    }
  }
  issues.push(...nodeIssues(rules, content.text_type_node_id, "text_type", "text_type_node_id"));
  issues.push(...nodeIssues(rules, content.part_node_id, "part", "part_node_id"));
  return issues;
}

function sharedOptionIssues(content: ContextContent, rules: ModuleRules): ContentIssue[] {
  const issues: ContentIssue[] = [];
  const options = content.shared_options ?? [];
  const expected = rules.optionCount(content.part_node_id);
  if (
    (expected !== null && options.length !== expected) ||
    !keysInOrder(options.map((o) => o.key))
  ) {
    issues.push(
      issue(
        "shared_options",
        "option_count",
        `La lista debe tener ${expected} opciones con claves desde la A, en orden.`,
      ),
    );
  }
  for (const option of options) {
    if (blank(option.text)) {
      issues.push(issue(`shared_options[${option.key}].text`, "required", "Escribe la opción."));
    }
    if (blank(option.feedback)) {
      issues.push(
        issue(
          `shared_options[${option.key}].feedback`,
          "option_feedback_required",
          `La opción ${option.key} necesita su retroalimentación.`,
        ),
      );
    }
  }
  return issues;
}

function nodeIssues(
  rules: ModuleRules,
  id: string | null | undefined,
  kind: TaxonomyNode["kind"],
  field: string,
): ContentIssue[] {
  if (!id) {
    return rules.hasKind(kind)
      ? [issue(field, "required", "Falta la categoría del contexto.")]
      : [];
  }
  const node = rules.node(id);
  if (!node) return [issue(field, "taxonomy_unknown", "La categoría no existe en el módulo.")];
  if (node.kind !== kind) {
    return [issue(field, "taxonomy_mismatch", `El código ${node.code} no corresponde.`)];
  }
  return [];
}

// --------------------------------------------------------------------- esquemas zod

/** Lleva cada problema a zod con su `field` y su `rule` en `params`. */
function refineWith<T>(collect: (value: T) => ContentIssue[]) {
  return (value: T, ctx: z.RefinementCtx) => {
    for (const found of collect(value)) {
      ctx.addIssue({
        code: "custom",
        message: found.message,
        path: fieldPath(found.field),
        params: { field: found.field, rule: found.rule },
      });
    }
  };
}

/** `options[B].feedback` → `["options", "B", "feedback"]`. */
function fieldPath(field: string): string[] {
  return field.split(/[.[\]]+/).filter(Boolean);
}

export function itemContentSchema(
  kind: ItemKind,
  module: ContentModule,
  options: ItemRuleOptions = {},
) {
  const rules = new ModuleRules(module, options.rubricIds);
  return itemShape.superRefine(
    refineWith<z.infer<typeof itemShape>>((value) =>
      itemIssues(kind, value as ItemContent, rules, options),
    ),
  );
}

export function contextContentSchema(module: ContentModule) {
  const rules = new ModuleRules(module);
  return contextShape.superRefine(
    refineWith<z.infer<typeof contextShape>>((value) =>
      contextIssues(value as ContextContent, rules),
    ),
  );
}

function toIssues(error: z.ZodError): ContentIssue[] {
  return error.issues.map((found) => {
    const params = (found as { params?: { field?: string; rule?: ValidationRule } }).params;
    return {
      field: params?.field ?? found.path.map(String).join("."),
      rule: params?.rule ?? "invalid_value",
      message: found.message,
    };
  });
}

/** Problemas de un ítem, en el orden en que los reporta el servidor. */
export function validateItem(
  kind: ItemKind,
  content: ItemContent,
  module: ContentModule,
  options: ItemRuleOptions = {},
): ContentIssue[] {
  const result = itemContentSchema(kind, module, options).safeParse(content);
  return result.success ? [] : toIssues(result.error);
}

export function validateContext(content: ContextContent, module: ContentModule): ContentIssue[] {
  const result = contextContentSchema(module).safeParse(content);
  return result.success ? [] : toIssues(result.error);
}
