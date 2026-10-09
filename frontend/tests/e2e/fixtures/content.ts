/**
 * Datos del banco de ítems para las pruebas e2e (002). Copia un ítem del banco inicial con un
 * código propio de la prueba, En revisión, para no depender del estado de los ítems del banco
 * entre corridas. Los códigos empiezan por `AAA-` para quedar primeros en los listados.
 */
import { randomBytes } from "node:crypto";

import { psqlExec } from "./db";

export function newItemCode(): string {
  return `AAA-E2E-${randomBytes(3).toString("hex").toUpperCase()}`;
}

/** Ítem En revisión copiado de `source`; `authorEmail` lo deja como autor (y contribuyente). */
export function cloneItemInReview(source: string, code: string, authorEmail?: string): void {
  psqlExec(
    `WITH author AS (
       SELECT id FROM identity.users WHERE lower(email) = lower(:'author') LIMIT 1
     ), item AS (
       INSERT INTO content.items (code, module_code, kind, origin)
       SELECT :'code', module_code, kind, 'teacher' FROM content.items WHERE code = :'source'
       RETURNING id
     )
     INSERT INTO content.item_versions (item_id, number, state, context_version_id, difficulty,
       competence_id, assertion_id, evidence_id, component_id, situation_id, part_id, stem_md,
       options, answer_key, explanation_md, prompt_context_md, rubric_id, content_hash,
       fingerprint, author_id, contributor_ids, submitted_at)
     SELECT (SELECT id FROM item), 1, 'in_review', v.context_version_id, v.difficulty,
       v.competence_id, v.assertion_id, v.evidence_id, v.component_id, v.situation_id, v.part_id,
       v.stem_md || ' (' || :'code' || ')', v.options, v.answer_key, v.explanation_md,
       v.prompt_context_md, v.rubric_id, v.content_hash, sha256(:'code'::bytea),
       (SELECT id FROM author),
       COALESCE(ARRAY(SELECT id FROM author), '{}'), now()
     FROM content.item_versions v JOIN content.items i ON i.id = v.item_id
     WHERE i.code = :'source' ORDER BY v.number LIMIT 1;`,
    { code, source, author: authorEmail ?? "" },
  );
}
