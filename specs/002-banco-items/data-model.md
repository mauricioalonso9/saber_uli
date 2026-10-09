# Data Model: Banco de ítems

**Feature**: `002-banco-items` | **Fecha**: 2026-10-09 | **Plan**: [plan.md](./plan.md)

Modelo de dominio y su persistencia en PostgreSQL 18. Las convenciones son las de
[001](../001-identidad-acceso/data-model.md):

- nombres de tablas y columnas en inglés y descripciones en español;
- claves `uuid DEFAULT uuidv7()`;
- fechas `timestamptz` en UTC.

Esquema nuevo: `content`. Ningún otro contexto lo lee directamente (principio II). Las
referencias a usuarios (`*_by`, `author_id`…) son identificadores de `identity.users` **sin clave
foránea entre esquemas**. Los nombres se piden a la fachada de `identity` (research R-14).

---

## 1. Agregados y entidades del dominio

| Agregado (raíz) | Entidades y objetos de valor | Requisitos |
|-----------------|------------------------------|------------|
| `Module` | `TaxonomyNode` (árbol por tipo), `ExamTarget` (meta y pesos) | FR-001…004, 039, 040, 045 |
| `Rubric` | `RubricDimension`, `RelevanceCondition` | FR-004 |
| `Context` | `ContextVersion`, `SharedOption` | FR-005, 007, 009, 020, 026 |
| `Item` | `ItemVersion`, `Option` (texto, correcta, retroalimentación), `TaxonomyTags`, `ContentHash`, `Fingerprint` | FR-002, 003, 006, 008, 010…018 |
| `ItemEvent` | — (solo inserción; historia y auditoría) | FR-018, 047 |
| `Media` | — | FR-009 |
| `ImportJob` | `ImportRow` (resultado por ítem), `OriginalityDeclaration` | FR-028…037 |
| `ExportRecord` | — (solo inserción) | FR-038, 047 |
| `SeedLoad` | — (solo inserción) | FR-021…023 |
| `VersionStatistics` | `OptionShare`, `ProblemSignal` | FR-041…044 |

Reglas del dominio que no dependen de la base:

- **Validación del contenido por tipo**: `ItemVersion.validate(module_rules)`.
  - `selection`: exactamente una opción correcta; número de opciones según el módulo o la parte;
    retroalimentación en cada opción; explicación general; taxonomía requerida por el módulo.
  - `matching` (Inglés parte 1): clave existente entre las opciones compartidas del contexto; sin
    opciones propias. El contexto tiene exactamente `part_options` (8) opciones compartidas y
    como máximo 5 ítems de emparejamiento (FR-003).
  - `writing_prompt`: pregunta, contexto en texto y rúbrica; sin opciones.
- **Palabras de Lectura crítica**: `WordCount.of(markdown)`, con máximo de 500 (research R-10).
- **Transiciones**: la máquina de estados de §4. La autoaprobación se impide con
  `contributor_ids` (FR-012).
- **Huellas**: `ContentHash` y `Fingerprint` (research R-06).
- **Estadísticas**: `compute_statistics(first_responses)`, con un mínimo de 30 (research R-13).

---

## 2. Tablas del esquema `content`

### 2.1 `modules`

| Columna | Tipo | Notas |
|---------|------|-------|
| `code` | text PK | `LC`, `RC`, `CC`, `ING`, `CE` |
| `name` | text | |
| `question_type` | text | `CHECK (question_type IN ('selection','writing'))` |
| `options_per_item` | smallint NULL | 4 en LC, RC y CC; NULL cuando depende de la parte (Inglés) o no aplica (CE) |
| `max_context_words` | smallint NULL | 500 en LC |
| `exam_questions` | smallint | 30, 30, 30, 45, 1 (constitución) |
| `bank_target` | integer | meta de ítems publicados para la cobertura (150; 225 en Inglés; 20 en CE) |
| `position` | smallint | orden de presentación |

La carga del banco inicial crea los cinco módulos. El administrador edita solo `bank_target`.

### 2.2 `taxonomy_nodes`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `module_code` | text FK → `modules.code` | |
| `kind` | text | `CHECK (kind IN ('competence','assertion','evidence','component','situation','text_type','part'))` |
| `code` | text | código de negocio (`LC-A1`, `RC-COMP-EST`, `ING-P4`…) |
| `name` | text | |
| `description` | text NULL | |
| `parent_id` | uuid NULL FK → `taxonomy_nodes.id` | evidencia → afirmación → competencia |
| `target_weight` | numeric(4,3) NULL | `CHECK (target_weight BETWEEN 0 AND 1)`; `peso_aprox` del banco inicial |
| `part_options` | smallint NULL | solo `part`: número de opciones (8 en la parte 1, 3 en las partes 2 a 5, 4 en las partes 6 y 7) |
| `part_format` | text NULL | solo `part`: `CHECK (part_format IN ('matching','selection'))` |
| `active` | boolean DEFAULT true | FR-045: inactiva no se ofrece en ítems nuevos |
| `position` | smallint | |

- `UNIQUE (code)`.
- `CHECK`: una `evidence` tiene padre `assertion`, y una `assertion` tiene padre `competence`.
  Lo verifican la aplicación y una prueba de integración.
- Borrar una categoría usada por alguna versión responde 409 `taxonomy-node-in-use` (FR-045).
- La suma de `target_weight` por módulo y tipo debe estar entre 0.95 y 1.05. Se valida al guardar
  e informa sin bloquear, porque los pesos del ICFES son aproximados.

### 2.3 `rubrics`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `code` | text UNIQUE | `RUB-CE-01` |
| `name` | text | |
| `note` | text NULL | |
| `relevance_condition` | jsonb | `{name, description}` |
| `dimensions` | jsonb | `[{code, name, levels: [{level, description}]}]`; el formato se valida en el dominio |
| `active` | boolean DEFAULT true | |

### 2.4 `media`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `sha256` | bytea UNIQUE | huella de la imagen ya re-codificada (research R-11) |
| `content_type` | text | `CHECK (content_type IN ('image/png','image/jpeg','image/webp'))` |
| `width`, `height` | integer | ≤ 4 000 |
| `size_bytes` | integer | `CHECK (size_bytes <= 1048576)` |
| `data` | bytea | |
| `created_by` | uuid | |
| `created_at` | timestamptz | |

### 2.5 `contexts` y `context_versions`

`contexts`:

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `code` | text UNIQUE | `LC-CTX-001` |
| `module_code` | text FK → `modules.code` | |
| `current_version_id` | uuid NULL FK → `context_versions.id` | `DEFERRABLE INITIALLY DEFERRED` |
| `seed_hash` | bytea NULL | huella del contexto en la última carga del banco inicial (R-07) |
| `revision` | integer DEFAULT 0 | sube con cada cambio; es el `ETag` (R-09) |
| `created_at` | timestamptz | |

`context_versions` (inmutables una vez creadas):

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `context_id` | uuid FK → `contexts.id` | |
| `number` | integer | `UNIQUE (context_id, number)` |
| `kind` | text | `CHECK (kind IN ('text','table','image','shared_options'))` |
| `title` | text | |
| `body_md` | text NULL | Markdown (R-10); las tablas van aquí |
| `media_id` | uuid NULL FK → `media.id` | `kind = 'image'` |
| `alt_text` | text NULL | `CHECK (kind <> 'image' OR length(trim(alt_text)) > 0)` (FR-009) |
| `text_type_node_id` | uuid NULL FK → `taxonomy_nodes.id` | LC: tipo de texto |
| `part_node_id` | uuid NULL FK → `taxonomy_nodes.id` | Inglés |
| `subtype` | text NULL | p. ej. `columna_de_opinion` |
| `shared_options` | jsonb NULL | `kind = 'shared_options'`: `[{key, text, feedback}]` |
| `word_count` | integer NULL | calculado en LC; `CHECK (word_count IS NULL OR word_count <= 500)` |
| `origin` | text | `CHECK (origin IN ('seed','teacher','ai'))` |
| `content_hash` | bytea | R-06 |
| `created_by` | uuid NULL | NULL en la carga del banco inicial |
| `created_at` | timestamptz | |

### 2.6 `items`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `code` | text UNIQUE | `LC-0001`, `CE-0001` (FR-008) |
| `module_code` | text FK → `modules.code` | |
| `kind` | text | `CHECK (kind IN ('selection','matching','writing_prompt'))` |
| `origin` | text | `CHECK (origin IN ('seed','teacher','ai'))` |
| `seed_hash` | bytea NULL | R-07 |
| `revision` | integer DEFAULT 0 | sube con cada cambio de cualquiera de sus versiones; es el `ETag` (R-09, FR-027) |
| `created_at` | timestamptz | |

### 2.7 `item_versions`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `item_id` | uuid FK → `items.id` | |
| `number` | integer | `UNIQUE (item_id, number)` |
| `state` | text | `CHECK (state IN ('draft','in_review','published','retired'))` |
| `context_version_id` | uuid NULL FK → `context_versions.id` | la versión del contexto que fija (R-02) |
| `difficulty` | text | `CHECK (difficulty IN ('low','medium','high'))` |
| `competence_id`, `assertion_id`, `evidence_id`, `component_id`, `situation_id`, `part_id` | uuid NULL FK → `taxonomy_nodes.id` | obligatoriedad según el módulo (FR-002, FR-003) |
| `stem_md` | text | enunciado; en CE, la pregunta |
| `options` | jsonb NULL | `selection`: `[{key, text, correct, feedback}]` |
| `answer_key` | text NULL | `matching`: clave entre las opciones compartidas del contexto |
| `explanation_md` | text | FR-006 |
| `prompt_context_md` | text NULL | CE: contexto de la consigna |
| `rubric_id` | uuid NULL FK → `rubrics.id` | CE (FR-004) |
| `content_hash` | bytea | R-06 |
| `fingerprint` | bytea | R-06; índice |
| `search` | tsvector GENERATED | `to_tsvector('spanish', stem_md ∥ explanation_md)`; índice GIN (R-12). Una columna generada solo ve su fila: el código del ítem y el título del contexto se buscan con `ILIKE` en la consulta |
| `author_id` | uuid NULL | quien la creó; NULL en la carga del banco inicial |
| `contributor_ids` | uuid[] | todas las personas que la crearon o modificaron (FR-012) |
| `submitted_at`, `submitted_by` | NULL | |
| `reviewed_at`, `reviewed_by` | NULL | aprobación, devolución o rechazo |
| `published_at` | timestamptz NULL | |
| `retired_at`, `retired_by`, `retire_reason` | NULL | `CHECK (state <> 'retired' OR retire_reason IS NOT NULL)` |
| `created_at`, `updated_at` | timestamptz | |

Índices e invariantes:

- `UNIQUE (item_id) WHERE state = 'published'`: a lo sumo una publicada (FR-011).
- `UNIQUE (item_id) WHERE state IN ('draft','in_review')`: a lo sumo una abierta (R-02).
- Índices por `(state)`, `(assertion_id)`, `(part_id)`, `(component_id)`, `(difficulty)` y
  `(fingerprint)`.
- Una versión `published` o `retired` es inmutable. El repositorio solo cambia `state` y las
  columnas de retiro (`published → retired`). Una prueba de integración intenta modificar el
  contenido y espera el error.
- Las respuestas de 003 referencian `item_versions.id` (FR-017).

### 2.8 `item_events` (solo inserción)

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `item_id` | uuid FK → `items.id` | |
| `version_id` | uuid NULL FK → `item_versions.id` | |
| `type` | text | catálogo de §5 |
| `actor_id` | uuid NULL | NULL = sistema (carga del banco inicial) |
| `occurred_at` | timestamptz | |
| `comment` | text NULL | devolución o comentario; texto del docente |
| `reason` | text NULL | rechazo o retiro |
| `details` | jsonb | sin datos personales: estados antes y después, `import_id`, confirmaciones del revisor, campos cambiados |

`saber_app` solo tiene `INSERT` y `SELECT` (FR-047). Índice `(item_id, occurred_at)`.

Los textos de `comment` y `reason` los escriben los docentes y se muestran en la historia. La
interfaz advierte que no se incluyan datos personales de estudiantes. No son datos personales del
autor, más allá de su autoría (§7).

### 2.9 `imports`

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `created_by` | uuid | |
| `created_at` | timestamptz | |
| `source_name` | text | nombre del archivo, sin la ruta |
| `format` | text | `CHECK (format IN ('json','xlsx'))` |
| `file_sha256` | bytea | |
| `status` | text | `CHECK (status IN ('pending','confirmed','expired'))` |
| `expires_at` | timestamptz | creación + 24 h (R-05) |
| `summary` | jsonb | conteos: nuevos, actualizaciones, sin cambios y con error |
| `rows` | jsonb | resultado por ítem: código, acción, diferencias y errores `[{field, rule, message}]` |
| `payload` | jsonb NULL | contenido normalizado listo para aplicar; se borra al confirmar o vencer |
| `target_state` | text NULL | `draft` o `in_review`, elegido al confirmar |
| `originality_declared` | boolean NULL | FR-036 |
| `confirmed_at` | timestamptz NULL | |
| `result` | jsonb NULL | lo aplicado: creados, versionados y omitidos `changed-since-preview` |

`saber_app` puede hacer `UPDATE` solo de `status`, `payload`, `target_state`,
`originality_declared`, `confirmed_at` y `result` (permisos de columna).

### 2.10 `exports` (solo inserción)

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | uuid PK | |
| `created_by` | uuid | |
| `created_at` | timestamptz | |
| `format` | text | `json`, `xlsx` |
| `filter` | jsonb | filtros aplicados |
| `version_choice` | text | `published`, `latest` |
| `item_count`, `skipped_count` | integer | `skipped_count`: ítems que la plantilla no representa |

### 2.11 `taxonomy_changes` (solo inserción)

`id`, `changed_by`, `changed_at`, `target` (`node`, `rubric` o `module`), `target_id`, `action`
(`created`, `updated`, `deactivated`, `reactivated` o `deleted`) y `before`/`after` (jsonb).

### 2.12 `seed_loads` (solo inserción)

`id`, `loaded_at`, `file_sha256`, `schema_version` y `summary` (jsonb con conteos de agregados,
versionados y sin cambios). También `pending_manual` (jsonb con los códigos que no se aplicaron
por tener una versión abierta, FR-022a).

### 2.13 `item_version_stats`

| Columna | Tipo | Notas |
|---------|------|-------|
| `version_id` | uuid PK FK → `item_versions.id` | |
| `first_responses` | integer | |
| `correct_rate` | numeric(5,4) NULL | NULL con menos de 30 respuestas |
| `option_rates` | jsonb NULL | `{A: 0.42, …}` |
| `discrimination` | numeric(5,4) NULL | punto-biserial corregida |
| `signals` | text[] | `too_easy`, `too_hard`, `negative_discrimination`, `distractor_beats_key` |
| `computed_at` | timestamptz | |

La tarea nocturna la reemplaza completa (R-13). Índice GIN en `signals`.

### 2.14 Roles y permisos de la base

`saber_app`:

- `SELECT`, `INSERT` y `UPDATE` sobre `modules`, `taxonomy_nodes`, `rubrics`, `contexts`,
  `items`, `item_versions` e `item_version_stats`;
- `DELETE` solo sobre `taxonomy_nodes` (una categoría sin uso) e `item_version_stats`; las
  importaciones vencidas no se borran, se marcan `expired` y pierden su `payload`;
- `INSERT` y `SELECT` sobre `media`, `context_versions`, `item_events`, `exports`,
  `taxonomy_changes` y `seed_loads`;
- sobre `imports`, los permisos de columna de §2.9.

El rol de migraciones es dueño del esquema. Lo mismo que 001/V20, verificado por una prueba de
infraestructura.

---

## 3. Esquema `shared`

Sin cambios. `content` no publica eventos al outbox en 002, porque no hay consumidores (YAGNI).
003 agregará `content.ItemVersionPublished` si lo necesita.

---

## 4. Máquina de estados de una versión de ítem

```text
            enviar (docente o admin)            aprobar (admin ∉ contributors)
  draft ─────────────────────────▶ in_review ─────────────────────────▶ published
    ▲                                 │  │                                  │
    │      devolver con comentarios   │  │ rechazar con motivo              │ retirar con motivo
    └─────────────────────────────────┘  └──────────────▶ retired ◀────────┘
                                                            ▲
                     aprobar una versión nueva del mismo ítem (la publicada pasa a retired)
```

| Desde | Acción | Hacia | Quién | Condiciones |
|-------|--------|-------|-------|-------------|
| — | crear o importar | `draft` o `in_review` | `content:author` | contenido válido para `in_review`; `draft` admite incompletos |
| `draft` | editar | `draft` | `content:author` | `If-Match`; agrega al editor a `contributor_ids` |
| `draft` | enviar | `in_review` | `content:author` | contenido válido (FR-024) |
| `in_review` | editar o reimportar | `draft` o `in_review` | `content:author` | FR-016: el docente elige; la revisión empieza de nuevo |
| `in_review` | aprobar | `published` | `content:review` | quien aprueba no está en `contributor_ids`; confirmaciones de FR-014; la publicada anterior pasa a `retired` |
| `in_review` | devolver | `draft` | `content:review` | comentario obligatorio |
| `in_review` | rechazar | `retired` | `content:review` | motivo obligatorio |
| `published` | retirar | `retired` | `content:review` | motivo obligatorio |
| `published` o `retired` | editar o reimportar con cambios | nueva versión `draft` o `in_review` | `content:author` | FR-015; la publicada sigue vigente |
| `published` | contexto editado | nueva versión `in_review` | sistema (por la edición) | FR-020 |

Si el único administrador activo está en `contributor_ids`, la aprobación responde 403
`self-approval-forbidden`. La cola de revisión marca esas versiones con
`needs_another_reviewer: true`.

---

## 5. Catálogo de eventos de la historia (`item_events.type`)

`created`, `edited`, `submitted`, `approved`, `returned`, `rejected`, `retired`,
`superseded` (la publicada anterior pasa a `retired` al aprobar la nueva), `commented`,
`imported` (con `import_id`), `seed_loaded`, `seed_versioned`, `context_changed` (versión creada
por FR-020) y `rebased_on_context` (versión abierta que pasa a la nueva versión del contexto).

---

## 6. Formato de intercambio v1 (resumen)

El formato está en `backend/schemas/banco_items.schema.json`, generado (research R-03). En
resumen:

```text
{ esquema_version: "1.0", nombre?, descripcion?, fuente_taxonomia?, estructura_examen?,
  modulos: [ {codigo, nombre, tipo_pregunta, opciones_por_item?, restricciones?,
              competencias?[afirmaciones[evidencias]], componentes?, situaciones?,
              tipos_texto?, partes?, aspectos_evaluados?} ],
  contextos: [ {id, modulo, titulo, contenido_md, tipo_texto?, subtipo?, parte?,
                opciones_compartidas?[{clave, texto, retroalimentacion}],
                imagen?{media_id, texto_alternativo}, palabras?, origen, estado} ],
  items: [ {id, version?, modulo, contexto_id?, competencia?, afirmacion?, evidencia?,
            componente?, situacion?, parte?, dificultad, enunciado,
            opciones?[{clave, texto, correcta, retroalimentacion}],
            usa_opciones_del_contexto?, clave_correcta?, explicacion, origen, estado} ],
  consignas_escritura: [ {id, version?, modulo:"CE", dificultad, contexto, pregunta,
                          rubrica_id, origen, estado} ],
  rubricas: [ {id, nombre, nota?, condicion_previa{nombre, descripcion},
               dimensiones[{codigo, nombre, niveles[{nivel, descripcion}]}]} ] }
```

Equivalencias con el modelo:

| Archivo | Modelo |
|---------|--------|
| `dificultad`: `baja`, `media`, `alta` | `low`, `medium`, `high` |
| `estado`: `borrador`, `en_revision`, `publicado`, `retirado` | `draft`, `in_review`, `published`, `retired` |
| `origen`: `ia`, `docente`, `banco_inicial` | `ai`, `teacher`, `seed` (`banco_inicial` identifica ítems escritos por personas que llegan en el banco inicial; los del banco actual traen `ia` y se guardan `ai`) |
| `usa_opciones_del_contexto: true` | `kind = matching` |
| consigna | `kind = writing_prompt` |

La plantilla XLSX tiene sus columnas en research R-04.

---

## 7. Datos personales en `content`

| Dato | Dónde | Tratamiento |
|------|-------|-------------|
| Identificador de autores, colaboradores, revisores e importadores | `item_versions`, `item_events`, `imports`, `exports`, `media`, `taxonomy_changes` | Solo el UUID; el nombre lo da `identity` y muestra "Cuenta eliminada" tras la supresión. Se incluye en "Mis datos" (sección `banco_de_items`) |
| Comentarios de revisión | `item_events.comment` | Texto de trabajo docente; la interfaz advierte no incluir datos de estudiantes |
| Respuestas de estudiantes | no se guardan en `content` | Las estadísticas son agregadas, sin identificador (FR-044) |
| Metadatos de imágenes | se eliminan al re-codificar | EXIF fuera (R-11) |

Los logs no incluyen textos de ítems ni nombres de archivo, solo identificadores y conteos
(principio V, 001/R-27).

---

## 8. Validaciones derivadas de los requisitos

| Regla | Dónde se garantiza |
|-------|-------------------|
| Una opción correcta; opciones según el módulo o la parte; retroalimentación en cada una; explicación (FR-002, 003, 006) | dominio (`ItemVersion.validate`) + prueba unitaria por módulo y parte |
| Lectura crítica ≤ 500 palabras (FR-007) | dominio (`WordCount`) + `CHECK` |
| Texto alternativo de imágenes (FR-009) | dominio + `CHECK` |
| Una versión publicada y una abierta por ítem (FR-011, R-02) | índices únicos parciales |
| Sin autoaprobación (FR-012) | dominio + prueba de integración con dos administradores |
| Solo administradores revisan (FR-013) | permiso `content:review` + prueba de contrato (403) |
| Versión nueva al editar lo publicado (FR-015) | aplicación + prueba de integración |
| Reimportación sin cambios no crea versiones (FR-035, SC-002) | `content_hash` + prueba de integración |
| Duplicados (FR-032) | `fingerprint` + prueba de integración |
| Todo o nada al confirmar (FR-034) | una transacción + prueba con fallo inyectado |
| Categoría en uso no se borra (FR-045) | aplicación + FK `RESTRICT` |
| Edición simultánea (FR-027) | `items.revision` / `contexts.revision` + `If-Match` + prueba de integración |
| Historia inmodificable (FR-047) | permisos de la base + prueba de infraestructura |
