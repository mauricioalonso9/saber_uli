/**
 * Datos del banco de ítems para las pruebas e2e (002). Copia ítems y contextos del banco inicial
 * con códigos propios de la prueba, para no depender del estado del banco entre corridas. Los
 * códigos empiezan por `AAA-` para quedar primeros en los listados.
 */
import { randomBytes } from "node:crypto";

import { psqlExec } from "./db";

function suffix(): string {
  return randomBytes(3).toString("hex").toUpperCase();
}

export function newItemCode(): string {
  return `AAA-E2E-${suffix()}`;
}

export function newContextCode(): string {
  return `AAA-CTX-${suffix()}`;
}

interface CloneOptions {
  /** Autor (y contribuyente) de la versión. */
  authorEmail?: string;
  state?: "in_review" | "published";
  /** Usa la versión vigente de este contexto en vez del contexto del original. */
  contextCode?: string;
}

/** Copia la primera versión de `source` como un ítem nuevo, En revisión o Publicado. */
export function cloneItem(source: string, code: string, options: CloneOptions = {}): void {
  psqlExec(
    `WITH author AS (
       SELECT id FROM identity.users WHERE lower(email) = lower(:'author') LIMIT 1
     ), context AS (
       SELECT current_version_id AS id FROM content.contexts WHERE code = :'context'
     ), item AS (
       INSERT INTO content.items (code, module_code, kind, origin)
       SELECT :'code', module_code, kind, 'teacher' FROM content.items WHERE code = :'source'
       RETURNING id
     )
     INSERT INTO content.item_versions (item_id, number, state, context_version_id, difficulty,
       competence_id, assertion_id, evidence_id, component_id, situation_id, part_id, stem_md,
       options, answer_key, explanation_md, prompt_context_md, rubric_id, content_hash,
       fingerprint, author_id, contributor_ids, submitted_at, published_at)
     SELECT (SELECT id FROM item), 1, :'state',
       COALESCE((SELECT id FROM context), v.context_version_id), v.difficulty,
       v.competence_id, v.assertion_id, v.evidence_id, v.component_id, v.situation_id, v.part_id,
       v.stem_md || ' (' || :'code' || ')', v.options, v.answer_key, v.explanation_md,
       v.prompt_context_md, v.rubric_id, v.content_hash, sha256(:'code'::bytea),
       (SELECT id FROM author),
       COALESCE(ARRAY(SELECT id FROM author), '{}'), now(),
       CASE WHEN :'state' = 'published' THEN now() END
     FROM content.item_versions v JOIN content.items i ON i.id = v.item_id
     WHERE i.code = :'source' ORDER BY v.number LIMIT 1;`,
    {
      code,
      source,
      author: options.authorEmail ?? "",
      state: options.state ?? "in_review",
      context: options.contextCode ?? "",
    },
  );
}

/** Ítem En revisión copiado de `source`; `authorEmail` lo deja como autor (y contribuyente). */
export function cloneItemInReview(source: string, code: string, authorEmail?: string): void {
  cloneItem(source, code, { authorEmail });
}

/** Copia la versión vigente del contexto `source` como un contexto nuevo. */
export function cloneContext(source: string, code: string): void {
  psqlExec(
    `WITH original AS (
       SELECT c.module_code, v.* FROM content.contexts c
       JOIN content.context_versions v ON v.id = c.current_version_id
       WHERE c.code = :'source'
     ), context AS (
       INSERT INTO content.contexts (code, module_code)
       SELECT :'code', module_code FROM original RETURNING id
     ), version AS (
       INSERT INTO content.context_versions (context_id, number, kind, title, body_md, media_id,
         alt_text, text_type_node_id, part_node_id, subtype, shared_options, word_count, origin,
         content_hash)
       SELECT (SELECT id FROM context), 1, kind, title || ' (' || :'code' || ')', body_md,
         media_id, alt_text, text_type_node_id, part_node_id, subtype, shared_options,
         word_count, 'teacher', sha256(:'code'::bytea)
       FROM original RETURNING id
     )
     SELECT count(*) FROM version;
     -- Una sentencia aparte: el UPDATE no vería la fila que insertó un CTE de la misma sentencia.
     UPDATE content.contexts c SET current_version_id = v.id
     FROM content.context_versions v
     WHERE v.context_id = c.id AND c.code = :'code';`,
    { code, source },
  );
}
