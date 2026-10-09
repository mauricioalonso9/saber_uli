/**
 * Nombres legibles de los campos que reportan el servidor y `schemas.ts` (`stem_md`,
 * `options[B].feedback`, `taxonomy.assertion_id`…). Un campo desconocido (por ejemplo, una columna
 * de la plantilla) se muestra tal cual.
 */
const NAMES: Record<string, string> = {
  code: "Código",
  module: "Módulo",
  kind: "Tipo de ítem",
  difficulty: "Dificultad",
  stem_md: "Enunciado",
  explanation_md: "Explicación general",
  options: "Opciones",
  answer_key: "Clave correcta",
  context_code: "Contexto",
  prompt_context_md: "Contexto de la consigna",
  rubric_id: "Rúbrica",
  title: "Título",
  body_md: "Texto",
  media_id: "Imagen",
  alt_text: "Texto alternativo",
  text_type_node_id: "Tipo de texto",
  part_node_id: "Parte",
  shared_options: "Opciones compartidas",
  "taxonomy.competence_id": "Competencia",
  "taxonomy.assertion_id": "Afirmación",
  "taxonomy.evidence_id": "Evidencia",
  "taxonomy.component_id": "Componente",
  "taxonomy.situation_id": "Tipo de situación",
  "taxonomy.part_id": "Parte",
};

const PARTS: Record<string, string> = {
  text: "Texto de la opción",
  feedback: "Retroalimentación de la opción",
  correct: "Opción correcta",
};

export function fieldLabel(field: string): string {
  const named = NAMES[field];
  if (named) return named;
  const option = /^(?:shared_)?options\[([A-H])\](?:\.(text|feedback|correct))?$/.exec(field);
  if (option) {
    const [, key, part] = option;
    return part ? `${PARTS[part]} ${key}` : `Opción ${key}`;
  }
  return field;
}
