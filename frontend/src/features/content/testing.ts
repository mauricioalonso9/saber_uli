/**
 * Datos de ejemplo de las pruebas del banco de ítems (002). Permisos de un docente y de un
 * administrador con el banco, e ítems con la forma del contrato.
 */
import type { Me, Permission } from "@/api/model";
import type {
  ContentModule,
  Item,
  ItemSummary,
  ItemVersion,
  TaxonomyNode,
} from "@/api/content/model";
import { sessionFor } from "@/features/admin/testing";

export const TEACHER_CONTENT: Permission[] = ["content:author"];
export const ADMIN_CONTENT: Permission[] = [
  "content:author",
  "content:review",
  "content:taxonomy_manage",
];

export function withPermissions(kind: "admin" | "teacher", extra: Permission[]): Me {
  const me = sessionFor(kind);
  return { ...me, permissions: [...me.permissions, ...extra] };
}

export function version(overrides: Partial<ItemVersion> = {}): ItemVersion {
  return {
    number: 1,
    state: "in_review",
    content: {
      difficulty: "low",
      context_code: null,
      taxonomy: {
        competence_id: null,
        assertion_id: null,
        evidence_id: null,
        component_id: null,
        situation_id: null,
        part_id: null,
      },
      stem_md: "¿Qué indica la expresión «la vuelve más visible»?",
      options: [
        { key: "A", text: "Hace evidente una distracción.", correct: true, feedback: "Correcto." },
        { key: "B", text: "Genera la distracción.", correct: false, feedback: "Lo contrario." },
        { key: "C", text: "Permite vigilar.", correct: false, feedback: "No habla de vigilancia." },
        { key: "D", text: "Mejora la visibilidad.", correct: false, feedback: "Es literal." },
      ],
      answer_key: null,
      explanation_md: "El autor dice que el celular no crea la distracción.",
      prompt_context_md: null,
      rubric_id: null,
    },
    context_version: null,
    content_issues: [],
    author: null,
    contributors: [],
    reviewer: null,
    created_at: "2026-10-09T12:00:00Z",
    submitted_at: "2026-10-09T12:00:00Z",
    published_at: null,
    retired_at: null,
    retire_reason: null,
    ...overrides,
  };
}

export function item(overrides: Partial<Item> = {}): Item {
  return {
    code: "LC-0001",
    module: "LC",
    kind: "selection",
    origin: "ai",
    revision: 0,
    published: null,
    open: version(),
    last_review_comment: null,
    can: {
      edit: true,
      submit: false,
      approve: true,
      return: true,
      reject: true,
      retire: false,
      approve_blocked_reason: null,
    },
    ...overrides,
  };
}

export function summary(overrides: Partial<ItemSummary> = {}): ItemSummary {
  return {
    code: "LC-0001",
    module: "LC",
    kind: "selection",
    origin: "ai",
    difficulty: "low",
    stem_excerpt: "¿Qué indica la expresión «la vuelve más visible»?",
    context_code: "LC-CTX-001",
    assertion_code: "LC-A1",
    part_code: null,
    published_version: null,
    open_version: { number: 1, state: "in_review" },
    retired: false,
    needs_another_reviewer: false,
    signals: [],
    updated_at: "2026-10-09T12:00:00Z",
    ...overrides,
  };
}

function node(
  id: string,
  module: ContentModule["code"],
  kind: TaxonomyNode["kind"],
  extra: Partial<TaxonomyNode> = {},
): TaxonomyNode {
  return {
    id,
    module,
    kind,
    code: id.toUpperCase(),
    name: id,
    active: true,
    in_use: false,
    ...extra,
  };
}

/** Módulos con su taxonomía mínima: LC (4 opciones, 500 palabras), ING (partes 1 y 2) y CE. */
export const MODULES: ContentModule[] = [
  {
    code: "LC",
    name: "Lectura crítica",
    question_type: "selection",
    options_per_item: 4,
    max_context_words: 500,
    exam_questions: 35,
    bank_target: 100,
    nodes: [
      node("lc-c1", "LC", "competence", { name: "Comprensión" }),
      node("lc-a1", "LC", "assertion", { parent_id: "lc-c1", name: "Identifica contenidos" }),
      node("lc-a2", "LC", "assertion", { parent_id: "lc-c1", name: "Comprende la estructura" }),
      node("lc-e1", "LC", "evidence", { parent_id: "lc-a1", name: "Entiende expresiones" }),
      node("lc-tt", "LC", "text_type", { name: "Continuo informativo" }),
    ],
  },
  {
    code: "ING",
    name: "Inglés",
    question_type: "selection",
    options_per_item: null,
    max_context_words: null,
    exam_questions: 45,
    bank_target: 100,
    nodes: [
      node("ing-p1", "ING", "part", { name: "Parte 1", part_options: 8, part_format: "matching" }),
      node("ing-p2", "ING", "part", { name: "Parte 2", part_options: 3, part_format: "selection" }),
    ],
  },
  {
    code: "CE",
    name: "Comunicación escrita",
    question_type: "writing",
    options_per_item: null,
    max_context_words: null,
    exam_questions: 1,
    bank_target: 10,
    nodes: [],
  },
];

export const RUBRICS = [
  {
    id: "0b6a0366-9b56-451a-9a19-49cbcbe21c1c",
    code: "RUB-ARG",
    name: "Texto argumentativo",
    note: null,
    active: true,
    relevance_condition: {},
    dimensions: [],
  },
];
