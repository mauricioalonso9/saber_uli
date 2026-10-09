/**
 * T053: los esquemas del editor reproducen las reglas del banco (T013 y T017) con los mismos
 * `field` y `rule` que devuelve el servidor en `errors[]`, para mostrar el error junto al campo
 * antes de enviar (FR-024).
 */
import { describe, expect, it } from "vitest";
import type { ContentModule, ContextContent, ItemContent, TaxonomyNode } from "@/api/content/model";
import { countWords, validateContext, validateItem } from "./schemas";

function node(
  id: string,
  module: ContentModule["code"],
  kind: TaxonomyNode["kind"],
  extra: Partial<TaxonomyNode> = {},
): TaxonomyNode {
  return { id, module, kind, code: id, name: id, active: true, in_use: false, ...extra };
}

const LC: ContentModule = {
  code: "LC",
  name: "Lectura crítica",
  question_type: "selection",
  options_per_item: 4,
  max_context_words: 500,
  exam_questions: 35,
  bank_target: 100,
  nodes: [
    node("lc-c1", "LC", "competence"),
    node("lc-a1", "LC", "assertion", { parent_id: "lc-c1" }),
    node("lc-e1", "LC", "evidence", { parent_id: "lc-a1" }),
    node("lc-tt", "LC", "text_type"),
  ],
};

const ING: ContentModule = {
  code: "ING",
  name: "Inglés",
  question_type: "selection",
  options_per_item: null,
  max_context_words: null,
  exam_questions: 45,
  bank_target: 100,
  nodes: [
    node("ing-p1", "ING", "part", { part_options: 8, part_format: "matching" }),
    node("ing-p2", "ING", "part", { part_options: 3, part_format: "selection" }),
  ],
};

const CE: ContentModule = {
  code: "CE",
  name: "Comunicación escrita",
  question_type: "writing",
  options_per_item: null,
  max_context_words: null,
  exam_questions: 1,
  bank_target: 10,
  nodes: [],
};

function options(keys: string, correct = "A") {
  return [...keys].map((key) => ({
    key,
    text: `Opción ${key}`,
    correct: key === correct,
    feedback: `Porque ${key}.`,
  }));
}

function lcItem(overrides: Partial<ItemContent> = {}): ItemContent {
  return {
    difficulty: "low",
    context_code: null,
    taxonomy: { competence_id: "lc-c1", assertion_id: "lc-a1", evidence_id: "lc-e1" },
    stem_md: "¿Cuál es la tesis?",
    options: options("ABCD"),
    explanation_md: "Está en el primer párrafo.",
    ...overrides,
  };
}

const rules = (issues: { field: string; rule: string }[]) =>
  issues.map(({ field, rule }) => `${field}:${rule}`);

describe("validateItem", () => {
  it("acepta un ítem completo de Lectura crítica", () => {
    expect(validateItem("selection", lcItem(), LC)).toEqual([]);
  });

  it("exige las opciones del módulo, una correcta y retroalimentación en cada una", () => {
    const content = lcItem({
      options: [
        ...options("AB", "A"),
        { key: "C", text: "Opción C", correct: true, feedback: " " },
      ],
    });

    expect(rules(validateItem("selection", content, LC))).toEqual(
      expect.arrayContaining([
        "options:option_count",
        "options:single_correct_option",
        "options[C].feedback:option_feedback_required",
      ]),
    );
  });

  it("exige la explicación general, salvo en una consigna", () => {
    expect(rules(validateItem("selection", lcItem({ explanation_md: "" }), LC))).toContain(
      "explanation_md:explanation_required",
    );
  });

  it("exige las categorías que el módulo tiene", () => {
    const content = lcItem({ taxonomy: { assertion_id: "lc-a1", evidence_id: "lc-e1" } });

    expect(rules(validateItem("selection", content, LC))).toContain(
      "taxonomy.competence_id:required",
    );
  });

  it("en Inglés cuenta las opciones de la parte", () => {
    const part2 = { part_id: "ing-p2" };
    const three = lcItem({ taxonomy: part2, options: options("ABC") });
    const four = lcItem({ taxonomy: part2, options: options("ABCD") });

    expect(validateItem("selection", three, ING)).toEqual([]);
    expect(rules(validateItem("selection", four, ING))).toContain("options:option_count");
  });

  it("la parte 1 de Inglés pide la clave entre las opciones del contexto", () => {
    const context: ContextContent = {
      kind: "shared_options",
      title: "Avisos",
      part_node_id: "ing-p1",
      shared_options: options("ABCDEFGH").map(({ key, text, feedback }) => ({
        key,
        text,
        feedback,
      })),
    };
    const matching = (answer_key: string | null): ItemContent => ({
      difficulty: "low",
      context_code: "ING-CTX-1",
      taxonomy: { part_id: "ing-p1" },
      stem_md: "You can't park here.",
      options: null,
      answer_key,
      explanation_md: "El aviso prohíbe estacionar.",
    });

    expect(validateItem("matching", matching("C"), ING, { context })).toEqual([]);
    expect(rules(validateItem("matching", matching("Z"), ING, { context }))).toContain(
      "answer_key:matching_key_unknown",
    );
    expect(rules(validateItem("matching", matching(null), ING, { context }))).toContain(
      "answer_key:required",
    );
    expect(
      rules(validateItem("selection", lcItem({ taxonomy: { part_id: "ing-p1" } }), ING)),
    ).toContain("taxonomy.part_id:taxonomy_mismatch");
  });

  it("una consigna pide su contexto y la rúbrica, no opciones ni explicación", () => {
    const prompt: ItemContent = {
      difficulty: "medium",
      taxonomy: {},
      stem_md: "¿Debe prohibirse el celular en clase?",
      options: null,
      explanation_md: "",
      prompt_context_md: null,
      rubric_id: null,
    };

    expect(rules(validateItem("writing_prompt", prompt, CE))).toEqual([
      "prompt_context_md:required",
      "rubric_id:required",
    ]);
  });
});

describe("validateContext", () => {
  const text = (body_md: string): ContextContent => ({
    kind: "text",
    title: "Desconectar para aprender",
    body_md,
    text_type_node_id: "lc-tt",
  });

  it("limita los textos de Lectura crítica a 500 palabras", () => {
    const issues = validateContext(text(Array(501).fill("palabra").join(" ")), LC);

    expect(rules(issues)).toEqual(["body_md:context_word_limit"]);
    expect(issues[0].message).toContain("501/500");
    expect(validateContext(text(Array(500).fill("palabra").join(" ")), LC)).toEqual([]);
  });

  it("exige el texto alternativo de una imagen", () => {
    const image: ContextContent = {
      kind: "image",
      title: "Infografía",
      media_id: "0b6a0366-9b56-451a-9a19-49cbcbe21c1c",
      alt_text: " ",
      text_type_node_id: "lc-tt",
    };

    expect(rules(validateContext(image, LC))).toEqual(["alt_text:alt_text_required"]);
  });

  it("la lista de opciones compartidas tiene las de la parte, con retroalimentación", () => {
    const shared: ContextContent = {
      kind: "shared_options",
      title: "Avisos",
      part_node_id: "ing-p1",
      shared_options: [
        { key: "A", text: "Uno", feedback: "Por uno." },
        { key: "B", text: "Dos", feedback: "" },
      ],
    };

    expect(rules(validateContext(shared, ING))).toEqual([
      "shared_options:option_count",
      "shared_options[B].feedback:option_feedback_required",
    ]);
  });
});

describe("countWords", () => {
  it("cuenta como el servidor: sin URL ni marcas, sin partir palabras compuestas", () => {
    expect(countWords("El franco-colombiano midió 3,5 m en l’aula.")).toBe(7);
    expect(countWords("Ver [la fuente](https://example.org/a-b-c) y ![foto](x.png)")).toBe(5);
    expect(countWords("1. Primero\n2. Segundo\n| a | b |")).toBe(4);
  });
});
