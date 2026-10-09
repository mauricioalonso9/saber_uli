---
description: "Tareas de implementación de 002-banco-items"
---

# Tasks: Banco de ítems: carga inicial, importación, actualización y revisión

**Input**: Documentos de diseño en `specs/002-banco-items/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml),
[quickstart.md](./quickstart.md), [ADR 0008](../../docs/adr/0008-banco-items-versiones-e-intercambio.md)

**Tests**: Obligatorias (constitución, principio IV: TDD no negociable). Cada tarea de prueba se
escribe primero y **debe fallar** antes de empezar la tarea de implementación que la sigue.

**Organization**: Tareas agrupadas por historia de usuario. Desde la fase 3, cada historia se
entrega y se prueba de forma independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: Historia de usuario de `spec.md` (US1 a US9).
- Cada tarea indica los archivos que toca, su criterio de **Terminado** y a quién se **asigna**.

## Convenciones de trabajo (dos modelos)

- **→ Qwen**: implementación bien definida. Qwen trabaja así:
  - ejecuta la tarea con `/speckit.implement`;
  - escribe primero la prueba y confirma que falla;
  - implementa lo mínimo para que pase;
  - ejecuta la suite del contexto `content`;
  - hace un commit por tarea (Conventional Commits, por ejemplo `feat(content): …`);
  - agrega bajo la tarea la línea `- Estado: lista para revisión`, **sin marcar la casilla**.

  No cambia `contracts/openapi.yaml`, `data-model.md` ni los ADR. Si algo no encaja, agrega
  `- Decisión pendiente: …` y sigue con lo demás.
- **→ Opus**: diseño, seguridad y revisión. Opus implementa las tareas de seguridad y revisa las
  marcadas "lista para revisión". Corrige, o devuelve con `- Devuelta: …`, y **marca la casilla**
  solo al aprobar.
- **Rutas**:
  - contexto nuevo en `backend/src/saber_uli/content/`;
  - pruebas en `backend/tests/{unit,integration,contract,infra}/content/` o en el archivo que se
    indique;
  - frontend en `frontend/src/features/content/` y `frontend/src/shared/content/`.
- **Pruebas con datos**: toda prueba con base de datos usa `postgres:18` real (Testcontainers),
  con las migraciones aplicadas. El reloj se inyecta (`Clock`).
- **Identificadores de las pruebas**: las fábricas crean usuarios con los roles necesarios
  mediante las fixtures de 001. Ninguna prueba depende de la hora real ni de un orden de ejecución.
- **Datos personales**: los logs y la historia de `content` solo llevan identificadores, códigos y
  conteos (principio V, research R-14).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencias, esqueleto del contexto `content`, contrato y cliente generado.

- [x] T001 Agregar a `backend/pyproject.toml` las dependencias de ejecución `python-multipart`, `openpyxl`, `defusedxml` y `pillow`, y actualizar `backend/uv.lock` (research R-04, R-05, R-11) → Qwen
  - Terminado: `uv sync --frozen` funciona; `uv run python -c "import multipart, openpyxl, defusedxml, PIL"` termina sin error; CI `backend-quality` en verde.
  - Estado (Opus, 2026-10-09): cerrada. También `types-openpyxl` (desarrollo) para `mypy --strict`.
- [x] T002 [P] Agregar a `frontend/package.json` `remark-gfm`, `remark-math`, `rehype-katex` y `katex` (para su hoja de estilos), y actualizar `package-lock.json` (research R-10) → Qwen
  - Terminado: `npm ci`, `npm run typecheck` y `npm run build` pasan; la licencia de cada paquete es MIT.
  - Estado (Opus, 2026-10-09): cerrada. remark-gfm 4.0.1, remark-math 6.0.0, rehype-katex 7.0.1 y katex 0.19.0 (MIT).
- [x] T003 Crear el esqueleto `backend/src/saber_uli/content/{domain,application,application/queries,infrastructure,infrastructure/interchange,infrastructure/repositories,api}/__init__.py` y las carpetas `backend/tests/{unit,integration}/content/`. Agregar `saber_uli.content` a los cinco contratos de `backend/.importlinter`: capas; dominio puro (también con `PIL`, `openpyxl` y `multipart` prohibidos en el dominio); aplicación sin frameworks (más `openpyxl`, `PIL`, `pydantic`); independencia con `identity` y `notifications` (excepción solo para `*.application.public`); y kernel compartido → Qwen
  - Terminado: `uv run lint-imports` pasa con los cinco contratos y el contexto nuevo; `tests/infra/test_containers.py::test_import_linter` en verde.
  - Estado (Opus, 2026-10-09): cerrada. No existe `test_import_linter`: CI ejecuta `lint-imports` (5 contratos KEPT). `pydantic` sigue permitido en la capa de aplicación, como en 001.
- [x] T004 [P] Agregar a `frontend/orval.config.ts` un segundo destino desde `../specs/002-banco-items/contracts/openapi.yaml` hacia `src/api/content/`, con el mismo mutador y cabecera de "CÓDIGO GENERADO". Generar el cliente y confirmar que el paso de CI "cliente Orval sin diferencias" cubre las dos carpetas → Qwen
  - Terminado: `npm run api:generate` no deja diferencias; `npm run typecheck` pasa; CI `frontend-quality` en verde.
  - Estado (Opus, 2026-10-09): cerrada. El destino de 001 limpia solo `*.ts` y `model/**` para no borrar `src/api/content/`.
- [x] T005 Agregar la suite de contrato `backend/tests/contract/test_content_contract.py`. Usa Schemathesis sobre `specs/002-banco-items/contracts/openapi.yaml` contra la app ASGI, con usuarios Docente y Administrador con sesión privilegiada, y recorre solo las operaciones implementadas. Cambiar la verificación de operaciones implementadas de `backend/src/saber_uli/main.py` para que use la unión de los contratos de 001 y 002 (research R-15) → Opus
  - Terminado: la suite corre (0 operaciones implementadas al inicio); la verificación falla si una ruta de `content` no está en el contrato de 002.
  - Estado (Opus, 2026-10-09): cerrada. La comprobación de operaciones vive en `tests/contract/` (no en `main.py`): `implemented_content_operations.py` y una prueba de que toda ruta `/api/v1/content` de la app está en el contrato de 002.
- [x] T006 Prueba y cambio de permisos: en `backend/tests/unit/identity/test_permissions.py`, Docente tiene `content:author`; Administrador tiene además `content:review` y `content:taxonomy_manage`; Estudiante, Invitado y Director no tienen ninguno. Luego agregar los tres valores a `Permission` y a `ROLE_PERMISSIONS` en `backend/src/saber_uli/identity/domain/permissions.py`, y al enum `Permission` de `specs/001-identidad-acceso/contracts/openapi.yaml` (ampliación compatible, research R-08). Regenerar el cliente orval → Opus
  - Terminado: la prueba falló antes del cambio y pasa después; `GET /api/v1/me` de un docente incluye `content:author`; suites de contrato de 001 en verde.
  - Estado (Opus, 2026-10-09): cerrada. La prueba falló antes del cambio. También se actualizaron las expectativas de 001 que listan los permisos del docente (`test_me`, `test_role_rules`, `test_auth_dependency`); contrato de 001 en verde (55 operaciones).
- [x] T007 [P] Prueba: `backend/tests/integration/identity/test_user_directory_display_names.py` para `UserDirectory.display_names(ids)`. Devuelve `{id: nombre}` para cuentas activas, "Cuenta eliminada" para cuentas suprimidas (lápida) y omite los identificadores desconocidos; una sola consulta para N ids (research R-14) → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló por `ImportError` antes de T008.
- [x] T008 Implementar `display_names` en `backend/src/saber_uli/identity/application/public.py` (protocolo) y en `identity/application/directory.py` (`IdentityDirectory`) para que pase T007 → Qwen
  - Terminado: T007 en verde; `lint-imports` en verde.
  - Estado (Opus, 2026-10-09): cerrada. `UserRepository.names(ids)` hace una sola consulta; una cuenta sin nombre aparece como "Sin nombre". Suites `unit` e `integration` en verde (796).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Esquema `content`, dominio común (reglas por módulo y parte, validación, huellas,
estados), persistencia, formato de intercambio, ETag y base del frontend. **Bloquea todas las
historias.**

### Esquema de datos

- [x] T009 Prueba: `backend/tests/integration/content/test_schema.py` sobre la base migrada. Verifica:
  - existen las 14 tablas de data-model §2;
  - `UNIQUE (item_id) WHERE state = 'published'` y `UNIQUE (item_id) WHERE state IN ('draft','in_review')` rechazan una segunda versión;
  - los `CHECK` de `state`, `kind`, `origin`, `difficulty`, `content_type IN ('image/png','image/jpeg','image/webp')`, `size_bytes <= 1048576`, `word_count IS NULL OR word_count <= 500`, `kind <> 'image' OR length(trim(alt_text)) > 0` y `state <> 'retired' OR retire_reason IS NOT NULL`;
  - `taxonomy_nodes.code` único;
  - la columna `search` generada con `to_tsvector('spanish', …)` y su índice GIN.

  → Opus
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló (12) antes de 0008. Se prueba con `saber_migrator` en una transacción revertida.
- [x] T010 Crear `backend/migrations/versions/0008_content_schema.py` con el esquema `content` y las tablas, índices, `CHECK` y FK exactamente como en data-model §2.1 a §2.13 (FK `contexts.current_version_id` `DEFERRABLE INITIALLY DEFERRED`; FK de taxonomía `ON DELETE RESTRICT`) para que pase T009 → Qwen
  - Terminado: T009 en verde; `alembic downgrade -1` y `upgrade head` funcionan.
  - Estado (Opus, 2026-10-09): cerrada. 12 en verde; ida y vuelta 0008 → 0007 → head comprobada. `search` cubre enunciado y explicación (una columna generada no ve otras tablas); data-model y R-12 corregidos.
- [x] T011 [P] Prueba de infraestructura: `backend/tests/infra/test_content_grants.py`. Con el rol `saber_app`, `UPDATE` y `DELETE` sobre `content.item_events`, `context_versions`, `media`, `exports`, `taxonomy_changes` y `seed_loads` responden `permission denied`. `UPDATE` de `imports.rows` también responde `permission denied`, pero `UPDATE` de `imports.status` funciona. `DELETE` de `taxonomy_nodes` funciona y `DELETE` de `imports` responde `permission denied` (data-model §2.14) → Opus
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Va en `backend/tests/integration/content/test_db_grants.py` (Testcontainers, como `identity/test_db_grants.py`), no en `tests/infra/` (que levanta Compose). Falló con 11 errores antes de 0009.
- [x] T012 Crear `backend/migrations/versions/0009_content_grants.py` con los permisos de data-model §2.14 (incluidos los permisos de columna de `imports`) para que pase T011 → Opus
  - Terminado: T011 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 11 en verde. Además de §2.14: sin `DELETE` sobre ítems ni versiones, y sin DDL ni `TRUNCATE`.

### Dominio común

- [x] T013 [P] Prueba: `backend/tests/unit/content/test_module_rules.py`. Reglas por módulo y parte con datos de taxonomía en memoria:
  - LC, RC y CC exigen 4 opciones; LC exige `competence`, `assertion` y `evidence` coherentes (la evidencia pertenece a la afirmación y esta a la competencia); RC además `component` y `situation`; CC competencia, afirmación y evidencia.
  - Inglés exige `part`: la parte 1 es `matching` sin opciones propias; las partes 2 a 5 tienen 3 opciones y las 6 y 7, 4.
  - El contexto de la parte 1 tiene exactamente `part_options` (8) opciones compartidas (regla `option_count`), y un contexto admite como máximo 5 ítems de emparejamiento (regla `option_count`, FR-003).
  - CE exige rúbrica y no admite opciones.
  - Una categoría `active = false` es inválida en ítems nuevos y válida en ítems que ya la usan (FR-045).

  → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T014. Las etiquetas obligatorias salen de los tipos de categoría que tiene cada módulo (datos, FR-001); taxonomía de prueba en `tests/unit/content/taxonomy_fixtures.py`.
- [x] T014 Implementar `content/domain/module.py`, `taxonomy.py` y `rubric.py` (`Module`, `TaxonomyNode`, `TaxonomyNodeKind`, `ModuleRules`, `Rubric` con dimensiones de al menos 2 niveles) para que pase T013 → Qwen
  - Terminado: T013 en verde; sin importaciones de frameworks.
  - Estado (Opus, 2026-10-09): cerrada. 19 en verde. Además `content/domain/validation.py` (`ValidationRule`, `ContentIssue`), compartido por módulo, ítem y contexto.
- [x] T015 [P] Prueba: `backend/tests/unit/content/test_word_count.py` (research R-10). Un texto de exactamente 500 palabras se acepta y uno de 501 no. Las marcas Markdown (`**`, `#`, `>`), los separadores de tabla `|---|` y las URL de enlaces no cuentan. Los números y las palabras con tilde o con guion cuentan como una. Los 3 contextos de LC del banco inicial dan el valor de `palabras` del archivo con ±2 de tolerancia → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló antes de T016.
- [x] T016 Implementar `content/domain/word_count.py` para que pase T015 → Qwen
  - Terminado: T015 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 10 en verde; los tres textos de LC del banco inicial quedan dentro de ±2 de su `palabras`.
- [x] T017 [P] Prueba: `backend/tests/unit/content/test_item_validation.py`. `ItemVersion.validate(rules)` devuelve problemas con `field`, `rule` y `message`, con `rule` del catálogo `ValidationRule` del contrato:
  - `single_correct_option` con 0 o 2 opciones correctas;
  - `option_count`;
  - `option_feedback_required`;
  - `explanation_required`;
  - `taxonomy_unknown`, `taxonomy_inactive` y `taxonomy_mismatch`;
  - `matching_key_unknown` (la clave no está entre las opciones compartidas del contexto);
  - `option_count` en un contexto de opciones compartidas con un número distinto de `part_options`, y al agregar un sexto ítem de emparejamiento al mismo contexto;
  - `rubric_unknown`;
  - `context_word_limit`;
  - `alt_text_required`.

  Un Borrador incompleto se puede guardar, pero tiene `content_issues`; enviar a revisión exige cero problemas (FR-024) → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T018. Incluye la parte 1 de Inglés: exactamente 8 opciones compartidas y máximo 5 ítems por contexto (U1 de analyze).
- [x] T018 Implementar `content/domain/item.py`, `item_version.py`, `context.py` (con `SharedOption`, `ContextVersion` y validación de `kind`) y `errors.py` para que pase T017 → Qwen
  - Terminado: T017 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 53 en verde. `item_version.py` (tipos, `ItemContent`, `validate_item`), `context.py` (`ContextContent`, `ContextVersion`, `Context`, `validate_context`) y `errors.py`. El agregado `item.py` queda con la máquina de estados en T022.
- [x] T019 [P] Prueba: `backend/tests/unit/content/test_fingerprint.py` (research R-06):
  - `content_hash` es igual para el mismo contenido con claves en otro orden, con espacios externos o con Unicode NFC o NFD, y distinto si cambia una retroalimentación;
  - `fingerprint` es igual entre dos ítems que solo difieren en mayúsculas, tildes, puntuación, espacios u orden de las opciones, y distinto si cambia el texto de una opción.

  → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T020.
- [x] T020 Implementar `content/domain/fingerprint.py` (`ContentHash`, `Fingerprint`, SHA-256 sobre la forma canónica) para que pase T019 → Qwen
  - Terminado: T019 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 60 en verde (dominio). `content_hash` acepta cualquier valor (dataclasses, enums, UUID) y `normalize_text` queda disponible para la importación.
- [x] T021 [P] Prueba: `backend/tests/unit/content/test_lifecycle.py` con la máquina de estados de data-model §4. Prueba:
  - cada transición válida y que todas las demás lanzan `InvalidTransitionError` (`invalid-transition`);
  - aprobar con `approver ∈ contributor_ids` lanza `SelfApprovalError` (`self-approval-forbidden`, FR-012);
  - aprobar sin las dos confirmaciones es inválido (FR-014);
  - devolver exige comentario y rechazar o retirar exige motivo;
  - aprobar con otra versión publicada la marca `superseded`, que pasa a `retired`;
  - toda edición agrega al editor a `contributor_ids`;
  - cada transición produce el evento de historia de data-model §5.

  → Opus
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T022.
- [x] T022 Implementar `content/domain/lifecycle.py` y `content/domain/events.py` (tipos de evento de la historia) para que pase T021 → Opus
  - Terminado: T021 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 86 en verde (dominio). `lifecycle.py` (tabla de transiciones), `events.py` (`HistoryEventType`, `HistoryEvent`), entidad `ItemVersion` y agregado `item.py` (`Item`: crear, editar con `keep_in_review` y `start_state`, enviar, aprobar con reemplazo, devolver, rechazar, retirar y comentar). El comentario no sube la revisión.

### Persistencia y aplicación base

- [x] T023 [P] Prueba: `backend/tests/integration/content/test_repositories.py`. Comprueba que:
  - guardar y leer módulos, taxonomía, rúbricas, contextos con versiones, ítems con versiones, imágenes y eventos conserva todos los campos (`jsonb` de opciones, `contributor_ids`);
  - los repositorios rechazan modificar el contenido de una versión `published` o `retired`;
  - `items.revision` y `contexts.revision` suben con cada cambio;
  - `item_events` solo se inserta.

  → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló por `ModuleNotFoundError` antes de T024. Incluye la comparación del ORM con el esquema migrado (como en 001) y `tests/integration/content/conftest.py` (limpieza del esquema antes de cada prueba, fábrica de UoW y taxonomía de LC).
- [x] T024 Implementar `content/application/ports.py` (repositorios, `MediaProcessor`, `ResponseStatisticsSource`, `UserNames`), `content/application/unit_of_work.py`, `content/infrastructure/orm.py`, `content/infrastructure/repositories/*.py` y `content/infrastructure/unit_of_work.py` siguiendo el patrón de `identity`, para que pase T023 → Qwen
  - Terminado: T023 en verde; `mypy --strict` en verde.
  - Estado (Opus, 2026-10-09): cerrada. 9 en verde, a la primera. Repositorios en `repositories/catalog.py` (módulos, taxonomía, rúbricas), `contexts.py` (contextos e imágenes) e `items.py`; este último escribe con sentencias explícitas y retira primero para no violar los índices parciales al aprobar. Entidad `content/domain/media.py`. `MediaProcessor`, `ResponseStatisticsSource` y `UserNames` se agregan con su historia (US3, US8, US2).
- [x] T025 [P] Prueba: `backend/tests/unit/content/test_interchange.py` (research R-03, data-model §6). Comprueba que:
  - el banco inicial `backend/seeds/banco_inicial_saber_uli.json` se lee sin errores con 5 módulos, 8 contextos, 43 ítems, 3 consignas y 1 rúbrica;
  - las equivalencias `baja/media/alta → low/medium/high`, `en_revision → in_review` e `ia → ai` funcionan, y `usa_opciones_del_contexto: true` da `kind = matching`;
  - escribir y volver a leer un banco da el mismo contenido (`content_hash` iguales);
  - `esquema_version` distinto de `"1.0"` es `unreadable-file`.

  Además, `backend/tests/unit/content/test_interchange_schema.py` falla si `backend/schemas/banco_items.schema.json` difiere del JSON Schema generado → Qwen
  - Terminado: las dos pruebas fallan.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T026. Lee el banco inicial (5 módulos, 8 contextos, 46 ítems con 3 consignas, 1 rúbrica), comprueba equivalencias, ida y vuelta, errores por entrada y sobres ilegibles.
- [x] T026 Implementar `content/infrastructure/interchange/models.py` (Pydantic, formato v1), `json_format.py` (lector y escritor) y `schema.py` (generador). Generar y versionar `backend/schemas/banco_items.schema.json` (JSON Schema 2020-12) con el comando `uv run python -m saber_uli.content.infrastructure.interchange.schema > ../backend/schemas/banco_items.schema.json`, documentado en el docstring, para que pase T025 → Qwen
  - Terminado: T025 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 100 en verde (unidad). `interchange/models.py` (Pydantic, claves desconocidas rechazadas), `mapping.py`, `json_format.py` y `schema.py`; `backend/schemas/banco_items.schema.json` versionado. Especificaciones en `content/application/bundle.py`. Decisiones: regla nueva `invalid_value` (contrato ampliado) para valores con tipo equivocado; la explicación general no es obligatoria en consignas (la rúbrica cumple ese papel; el banco inicial no la trae); campos opcionales nuevos del formato documentados en `models.py`.
- [x] T027 [P] Prueba: `backend/tests/unit/content/test_etag.py` (research R-09). `ETag: "<revision>"`; `If-Match` igual pasa; distinto lanza 412 `edit-conflict` con `current` y `etag`; ausente lanza 428 `precondition-required`; se acepta el `ETag` débil `W/"7"` → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T028. Cubre también las respuestas HTTP (428, 412 con `current` y `etag`, 422 con `errors[].rule`).
- [x] T028 Implementar `content/api/etag.py` (dependencia FastAPI y problemas) para que pase T027 → Qwen
  - Terminado: T027 en verde.
  - Estado (Opus, 2026-10-09): cerrada. En verde. `content/api/etag.py` (`etag`, `expected_revision`, `require_revision`, `edit_conflict` y la dependencia `if_match_revision`). Ampliación compatible del kernel `shared/api/problems.py`: `FieldError.rule`, `ProblemException` con `errors` y `extensions`, errores de dominio con `issues` presentados en `errors[]`, y estados por slug 412, 428, 413 y 415.
- [x] T029 Prueba: `backend/tests/integration/content/test_content_access.py`. Recorre todas las rutas de `content` del contrato (con 404 aceptable para las no implementadas) y comprueba:
  - sin token responde 401;
  - sin sesión privilegiada responde 401 `reauthentication-required`, salvo `GET /content/media/{id}`;
  - un estudiante recibe 403 `forbidden`;
  - un docente recibe 403 en las rutas `content:review` y `content:taxonomy_manage`;
  - sin autorización de datos vigente responde 403 `consent-required`.

  → Opus
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló (404 y 0 operaciones revisadas) antes de T030. Revisa cada operación implementada del contrato; la cobertura crece sola con cada historia.
- [x] T030 Conectar el contexto en `backend/src/saber_uli/main.py`: unidad de trabajo de `content` en `app.state` y dependencias `require_permission` por router según `x-required-permission`. Sumar los routers vacíos de `content/api/*_router.py` bajo `/api/v1` con las guardias de sesión privilegiada y consentimiento, para que pase T029 → Qwen
  - Terminado: T029 en verde; suites de 001 en verde.
  - Estado (Opus, 2026-10-09): cerrada. En verde. `content/api/dependencies.py` (permisos como texto del contrato + sesión privilegiada; `reject_unknown_query` responde 422 a parámetros no declarados), `listContentModules` en `taxonomy_router.py` con `in_use` por categoría, y la UoW de content en `main.py`. Hallazgos: FastAPI envuelve los routers incluidos (`_IncludedRouter`) y `app.routes` ya no lista las rutas, así que la prueba de rutas dentro del contrato de T005 pasaba sin revisar nada; ahora usa `tests/routes.py` (`iter_route_contexts`). El contrato documenta 422 en las operaciones con parámetros de consulta. `.importlinter` permite `shared → identity.application.public` también en el contrato de independencia. Dos pruebas de 001 que reejecutan migraciones ahora migran hasta 0007 y marcan `head` (0008 no es repetible).

### Base del frontend

- [x] T031 [P] Prueba: `frontend/src/shared/content/ContentView.test.tsx` (research R-10, R-17). Comprueba que:
  - renderiza tablas GFM como `<table>` con encabezados;
  - `$x^2$` produce MathML (`<math>`);
  - el HTML crudo del Markdown no se renderiza;
  - una imagen se muestra con su `alt`;
  - en un ítem `matching` se muestran las opciones compartidas del contexto;
  - con `showFeedback` se ve la retroalimentación de cada opción y la explicación general;
  - axe no informa violaciones.

  → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló (módulo inexistente) antes de T032. axe se ejecuta con `axe-core` (agregado como dependencia de desarrollo explícita; ya venía transitivo con `@axe-core/playwright`) sin la regla de contraste, que jsdom no evalúa.
- [x] T032 Implementar `frontend/src/shared/content/MarkdownView.tsx` (react-markdown con `skipHtml`, remark-gfm, remark-math y rehype-katex con `output: "htmlAndMathml"`) y `ContentView.tsx`, e importar la hoja de estilos de KaTeX, para que pase T031 → Qwen
  - Terminado: T031 en verde; el paquete inicial no crece (ContentView se carga solo en rutas del banco).
  - Estado (Opus, 2026-10-09): cerrada. 9 en verde. `MarkdownView` (GFM, KaTeX con MathML, `skipHtml`; las tablas usan `ScrollRegion` de 001) y `ContentView` (selección, emparejamiento con opciones del contexto, consignas; `showFeedback`). El HTML crudo se descarta y su texto queda inerte.
- [x] T033 [P] Prueba: `frontend/src/app/navigation.test.tsx`. Un usuario con `content:author` ve "Banco de ítems" en la navegación; con `content:review` ve además "Revisión"; con `content:taxonomy_manage`, "Taxonomía"; un estudiante no ve ninguna. Las rutas `/banco*` y `/admin/taxonomia` sin el permiso muestran "No tienes permiso" → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló (9 de 10) antes de T034. Sin el permiso la ruta vuelve a `/inicio`, como el resto de rutas de gestión de 001 (no se muestra un aviso aparte).
- [x] T034 Registrar en `frontend/src/app/router.tsx` las rutas `/banco`, `/banco/revision`, `/banco/items/nuevo`, `/banco/items/$code`, `/banco/contextos/$code`, `/banco/importar`, `/banco/importaciones/$importId`, `/banco/exportar`, `/banco/cobertura` y `/admin/taxonomia` con `lazyRouteComponent` y páginas provisionales. Agregar las entradas de navegación por permiso y las claves `content.*` en `src/shared/i18n/es-CO`, para que pase T033 → Qwen
  - Terminado: T033 en verde; Lighthouse sigue ≥ 0.9.
  - Estado (Opus, 2026-10-09): cerrada. 225 pruebas de Vitest en verde. Rutas bajo demanda con páginas provisionales (`ContentPagePlaceholder`) que reemplazan las historias; `/banco/revision` se evalúa antes que `/banco`. Paquete inicial: 115 KB comprimido (antes 114).
- [x] T035 Revisión de seguridad de la fase 2 (Opus), anotada en `specs/002-banco-items/tasks.md`:
  - permisos y guardias de T029;
  - Markdown sin HTML crudo;
  - permisos de la base (T011);
  - inmutabilidad de versiones publicadas en los repositorios;
  - `import-linter`.

  Cierra la fase → Opus
  - Terminado: hallazgos corregidos o registrados; la fase 2 queda aprobada.
  - Estado (Opus, 2026-10-09): cerrada. Revisión de la fase 2 aprobada. (1) Permisos y guardias: T029 recorre cada operación implementada (401, 403 por consentimiento, 403 por permiso, 401 sin sesión privilegiada); parámetros de consulta desconocidos responden 422. (2) Markdown: `skipHtml` sin `rehype-raw`, filtro de URL por defecto; T031 lo prueba. (3) Base: T011 (historia, versiones de contexto, imágenes, exportaciones, cambios de taxonomía y cargas: solo inserción; `imports` solo cambia estado y resultado; sin DDL ni `TRUNCATE`). (4) Versiones publicadas o retiradas inmutables en el repositorio (T023). (5) import-linter: 5 contratos. Hallazgos corregidos: el lector JSON devolvía error interno (500) ante una anidación excesiva (`RecursionError`) y ante `preguntas_por_modulo` no numérico; ahora son `unreadable-file` o se ignoran, con pruebas en `test_interchange.py`. Pendiente para US4 (T065): límites de tamaño del archivo antes de leerlo.

**Checkpoint**: base lista; las historias pueden empezar.

---

## Phase 3: User Story 1 - Carga del banco inicial (Priority: P1) 🎯 MVP

**Goal**: cada despliegue aplica el banco inicial de forma idempotente. Agrega lo nuevo, versiona
lo cambiado en el archivo y nunca pisa el trabajo de los docentes.

**Independent Test**: desplegar desde cero y comprobar 46 ítems (43 + 3 consignas) y 8 contextos
En revisión con origen `ai`. Repetir: 0 cambios. Cargar un archivo actualizado: se agregan los
nuevos y se versionan los cambiados (quickstart B1 a B4).

### Tests for User Story 1 ⚠️

- [x] T036 [P] [US1] Prueba: `backend/tests/integration/content/test_seed_loader.py` (FR-021 a FR-023, R-07). Casos:
  - **Primera carga**: 5 módulos, la taxonomía con `target_weight` de `peso_aprox`, 1 rúbrica, 8 contextos (LC con `word_count`) y 46 ítems En revisión con origen `ai`, `author_id` NULL, evento `seed_loaded` y `seed_hash` guardado.
  - **Segunda carga igual**: 0 agregados y 0 versionados.
  - **Ítem editado por un docente**: queda intacto en la recarga.
  - **Archivo con `LC-9001` nuevo y `LC-0002` cambiado**: uno agregado y uno con versión nueva En revisión (`seed_versioned`).
  - **`LC-0001` cambiado con versión abierta de un docente**: queda en `pending_manual` y sin cambios (FR-022a).
  - **Taxonomía existente**: no se modifica; las categorías nuevas se agregan.
  - **Archivo con un ítem de dos opciones correctas**: lanza un error con el código y la regla `single_correct_option`, y no aplica nada.
  - **Dos cargas simultáneas**: una espera el *advisory lock* y la otra informa 0 cambios.
  - Cada carga deja una fila en `content.seed_loads`.

  → Opus
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T038 (8 casos).
- [x] T037 [P] [US1] Prueba: `backend/tests/integration/content/test_cli_load_seed.py`. Comprueba que:
  - `saber-uli content load-seed` termina con código 0 y registra el log `content_seed_loaded` con conteos (`added`, `versioned`, `unchanged`, `pending_manual`), sin textos de ítems ni rutas de archivo;
  - con `--file` inválido termina con código 1 y el log `content_seed_failed` trae solo el código del elemento y la regla.

  → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló antes de T039. El log de errores usa la clave `item` (no `code`): el procesador de logs de 001 enmascara `code` porque así se llama el código de OAuth.

### Implementation for User Story 1

- [x] T038 [US1] Implementar `content/application/seed_loader.py` (`SeedLoader`, con validación completa antes de aplicar, transacción única, *advisory lock* y comparación por `seed_hash`) para que pase T036 → Qwen
  - Terminado: T036 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 8 en verde. `seed_loader.py` (validación completa antes de aplicar, *advisory lock*, `seed_hash` por contexto e ítem, `pending_manual`), `resolution.py` (códigos → identificadores, huellas) y `context_changes.py` (FR-020, compartido con T057). Hallazgo: las columnas JSONB anulables guardaban el JSON `null` en vez de NULL desde sentencias explícitas; ahora usan `JSONB(none_as_null=True)`. Un ítem marcado publicado o retirado en el banco entra En revisión (constitución VI).
- [x] T039 [US1] Agregar a `backend/src/saber_uli/cli.py` el subcomando `content load-seed [--file RUTA]`, con la ruta por defecto `/app/seeds/banco_inicial_saber_uli.json` o `backend/seeds/…` en desarrollo. Cambiar el comando del servicio `migrate` en `compose.yaml` y en `infra/docker/backend-entrypoint.sh` para que ejecute `migrate` y luego `content load-seed`. Actualizar `backend/tests/infra/test_containers.py`, que debe comprobar que `migrate` termina con código 0 y que `content.items` tiene 46 filas tras `up`, para que pase T037 → Qwen
  - Terminado: T037 en verde; `docker compose up -d --wait` desde cero deja 46 ítems; un segundo `up` no cambia los conteos.
  - Estado (Opus, 2026-10-09): cerrada. 4 en verde. `saber-uli content load-seed [--file]` (usa `DATABASE_URL` o, en `migrate`, `MIGRATION_DATABASE_URL`); el punto de entrada de `migrate` encadena migraciones y carga; `SABER_SEEDS_DIR=/app/seeds` en la imagen. Comprobado en el stack local: primera ejecución 46 ítems, 8 contextos, 76 categorías y 1 rúbrica; la segunda, todo sin cambios. `tests/infra/test_containers.py` cuenta 46 ítems y repite `migrate` (prueba `full_stack`, se ejecuta en CI).
- [x] T040 [US1] Revisión de US1 (Opus), anotada en `specs/002-banco-items/tasks.md`: idempotencia, transacción, *advisory lock*, logs sin datos personales y escenarios B1 a B4 del quickstart → Opus
  - Terminado: B1 a B4 comprobados a mano; US1 aprobada.
  - Estado (Opus, 2026-10-09): cerrada. US1 aprobada. B2 a B4 los cubren `test_seed_loader.py` y `test_cli_load_seed.py` con PostgreSQL real; B1 comprobado en el stack local con `migrate` (46 ítems En revisión, origen `ai`); la vista en `/banco` se valida con la interfaz de US2 y US3 (T047, T063). Revisión: transacción única con validación previa, *advisory lock* como primera sentencia, logs solo con conteos y códigos (`item`), sin publicar nada sin revisión humana. Un ítem editado por un docente y luego publicado (sin versión abierta) recibe la versión del archivo En revisión sin tocar lo publicado (FR-022).

**Checkpoint**: el banco inicial queda cargado en todo entorno.

---

## Phase 4: User Story 2 - Revisión y publicación (Priority: P1) 🎯 MVP

**Goal**: los administradores aprueban, devuelven, rechazan y retiran; nadie aprueba lo que creó
o modificó; los docentes comentan.

**Independent Test**: con los ítems del banco inicial En revisión, un administrador aprueba uno
(pasa a Publicado), otro administrador comprueba que no puede aprobar lo que él mismo editó, y un
docente no ve las acciones (quickstart B5 a B8).

### Tests for User Story 2 ⚠️

- [x] T041 [P] [US2] Prueba: `backend/tests/integration/content/test_review.py` (FR-010 a FR-015, FR-018). Cubre:
  - **Aprobar**: requiere `confirms_alignment` y `confirms_originality`; deja `published`, `reviewed_by`, `published_at` y el evento `approved` con las confirmaciones en `details`; si había otra publicada, pasa a `retired` con el evento `superseded`.
  - **Autoaprobación**: aprobar siendo contribuyente lanza `self-approval-forbidden`.
  - **Devolver**: deja `draft` con el comentario.
  - **Rechazar**: deja `retired` con motivo, sin `published_at`.
  - **Retirar**: aplica a una publicada, con motivo.
  - **Transiciones inválidas**: responden `invalid-transition`.
  - **Revisión**: cada acción sube `items.revision`.
  - **Comentarios**: generan el evento `commented` sin cambiar el estado.

  → Opus
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Falló en la recolección antes de T044.
- [x] T042 [P] [US2] Prueba: `backend/tests/integration/content/test_items_api_review.py`. Cubre:
  - `approveItem`, `returnItem`, `rejectItem`, `retireItem` y `commentItem` según el contrato, con `If-Match`;
  - un docente recibe 403 en las cuatro primeras y 201 en `commentItem`;
  - `getItem.can`: `approve` es falso con `approve_blocked_reason = self_approval` para un contribuyente;
  - `listItems` con `state`, `module`, `origin`, `difficulty`, `taxonomy_node` (incluye descendientes), `q` (texto completo `spanish` sobre código, enunciado y título del contexto) y `awaiting_my_review` (excluye las versiones donde quien consulta es contribuyente), con paginación `PageMeta`;
  - `needs_another_reviewer` es verdadero si todos los administradores activos son contribuyentes;
  - `getItemHistory` lista versiones y eventos con `UserRef`, y una cuenta suprimida aparece como "Cuenta eliminada".

  → Qwen
  - Terminado: la prueba falla.
  - Estado (Opus, 2026-10-09): cerrada. Escrita y fallando (7 de 7) a la espera de T045.
- [ ] T043 [P] [US2] Prueba de componentes: `frontend/src/features/content/ReviewQueuePage.test.tsx` y `ReviewActions.test.tsx` (msw). Cubre:
  - la lista filtrada por módulo, con el origen "IA" visible;
  - aprobar exige marcar las dos confirmaciones;
  - devolver exige comentario y rechazar o retirar, motivo;
  - un 403 `self-approval-forbidden` muestra "Lo debe aprobar otro administrador";
  - un docente ve solo "Comentar";
  - los mensajes de estado tienen `role="status"`.

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 2

- [x] T044 [US2] Implementar `content/application/review.py` (`Review`: aprobar, devolver, rechazar, retirar y comentar, con eventos de historia) para que pase T041 → Qwen
  - Terminado: T041 en verde.
  - Estado (Opus, 2026-10-09): cerrada. 12 en verde. `content/application/review.py` (`Review` y `load_for_change`, que bloquea el ítem y compara la revisión esperada: `edit-conflict`). `HistoryEvent` gana `id` (lo asigna la persistencia), que la respuesta de `commentItem` necesita.
- [ ] T045 [US2] Implementar `content/application/queries/list_items.py`, `get_item.py` (con `can` y `needs_another_reviewer`) e `item_history.py`, con nombres vía `UserDirectory.display_names`, y `content/api/items_router.py` (`listItems`, `getItem`, `getItemHistory`, `commentItem`) y `review_router.py`, para que pase T042 → Qwen
  - Terminado: T042 en verde; las operaciones entran en la suite de T005.
  - En curso (Opus, 2026-10-09): hechos `active_admin_ids` en la fachada de identity, `content/domain/diff.py`, puertos `UserNames`, `ItemFilters`, `ItemSummaryRow` y en el repositorio `versions`, `count_matching_in_context`, `search` (filtros, texto completo, cola de revisión) y `version_numbers`. Faltan las consultas `get_item`, `list_items` e `item_history`, `content/api/schemas.py`, `items_router.py` y `review_router.py`, y la conexión en `main.py`.
- [ ] T046 [US2] Implementar `frontend/src/features/content/ReviewQueuePage.tsx`, `ReviewActions.tsx` y la vista de solo lectura de un ítem en `ItemEditorPage.tsx` (contenido con `ContentView` e historia) para que pase T043 → Qwen
  - Terminado: T043 en verde.
- [ ] T047 [US2] E2E: `frontend/tests/e2e/content-review.spec.ts`, con los escenarios B5 a B8 del quickstart, dos administradores, un docente y axe en `/banco/revision` → Qwen
  - Terminado: en verde con el perfil e2e (Chromium y WebKit).
- [ ] T048 [US2] Revisión de US2 (Opus), anotada en `specs/002-banco-items/tasks.md`: autoaprobación, permisos, confirmaciones registradas e inmutabilidad de lo publicado → Opus
  - Terminado: US2 aprobada.

**Checkpoint**: los ítems del banco inicial se pueden revisar y publicar.

---

## Phase 5: User Story 3 - Crear, editar y previsualizar ítems y contextos (Priority: P1) 🎯 MVP

**Goal**: los docentes crean y editan ítems, consignas y contextos con validación junto al campo y
vista previa móvil fiel. Editar lo publicado crea una versión nueva. Las ediciones simultáneas no
se pierden.

**Independent Test**: crear un ítem de RC con su contexto, previsualizarlo a 360 × 800, enviarlo a
revisión y comprobar las validaciones; editar un ítem publicado y ver que la versión publicada
sigue vigente (quickstart B9 a B13).

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Prueba: `backend/tests/integration/content/test_authoring.py` (FR-015, FR-016, FR-024, FR-027, FR-032). Cubre:
  - crear un ítem deja un Borrador con el autor como contribuyente;
  - un código existente responde `code-taken`;
  - un contenido igual al de otro ítem (`fingerprint`) responde `duplicate-item`;
  - guardar el borrador con `revision` vieja responde `edit-conflict`;
  - guardar sobre un ítem publicado sin versión abierta crea la versión N+1 en `draft`, y la publicada sigue intacta;
  - guardar sobre `in_review` vuelve a `draft` o se queda en `in_review` según el parámetro `keep_in_review` del contrato (falso por defecto, FR-016);
  - enviar con `content_issues` responde `validation-error` con la lista;
  - enviar sin problemas deja `in_review` con `submitted_by`;
  - los eventos `created`, `edited` y `submitted`;
  - si el autor pierde el rol Docente, su Borrador sigue en el banco y otro docente lo puede editar y enviar (caso límite de la spec).

  → Qwen
  - Terminado: la prueba falla.
- [ ] T050 [P] [US3] Prueba: `backend/tests/integration/content/test_contexts.py` (FR-005, FR-007, FR-020, FR-026). Cubre:
  - crear un contexto de texto, tabla, imagen u opciones compartidas;
  - la imagen sin `alt_text` responde `alt_text_required`;
  - un texto de LC de 501 palabras responde `context_word_limit` con el conteo;
  - editar crea `context_versions.number + 1`;
  - los ítems Publicados que lo usan reciben una versión nueva En revisión con el evento `context_changed`;
  - las versiones abiertas pasan a la nueva versión con `rebased_on_context`;
  - `getContext` da `item_count` y `published_item_count`;
  - `If-Match` obligatorio.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T051 [P] [US3] Prueba de seguridad: `backend/tests/integration/content/test_media.py` (FR-009, R-11). Cubre:
  - PNG, JPEG y WebP válidos se guardan re-codificados;
  - un JPEG con EXIF GPS queda sin EXIF;
  - SVG, GIF y un PNG truncado responden 415 `unsupported-media-type`;
  - más de 1 MB responde 413 `file-too-large`;
  - más de 4 000 px por lado responde 415;
  - la misma imagen dos veces devuelve el mismo `id`;
  - `GET /content/media/{id}` responde a un estudiante con `Cache-Control: private, max-age=31536000, immutable` y el `Content-Type` correcto si la imagen está en un contexto de una versión Publicada o Retirada, y 404 si solo la usan Borradores o versiones En revisión (FR-046); un docente la recibe siempre;
  - límite de 60 subidas por hora por usuario.

  → Opus
  - Terminado: la prueba falla.
- [ ] T052 [P] [US3] Prueba: `backend/tests/integration/content/test_items_api_authoring.py`. Cubre:
  - `createItem`, `saveItemDraft`, `submitItem`, `createContext`, `getContext`, `updateContext` y `getItemVersion` según el contrato;
  - `ETag` en las respuestas y 412 o 428 según `If-Match`;
  - `saveItemDraft?keep_in_review=true` sobre una versión En revisión la deja En revisión, y sin el parámetro la devuelve a Borrador;
  - `getItemVersion` devuelve `changes` campo por campo (`stem_md`, `options[B].feedback`, `taxonomy.assertion_id`) frente a la versión anterior;
  - `errors[]` de un 422 trae `field` y `rule`.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T053 [P] [US3] Prueba: `frontend/src/features/content/schemas.test.ts`. Los esquemas zod reproducen las reglas de T013 y T017 (opciones por módulo y parte, una correcta, retroalimentación, explicación, 500 palabras en LC, texto alternativo) con los mismos `rule` del contrato → Qwen
  - Terminado: la prueba falla.
- [ ] T054 [P] [US3] Prueba de componentes: `frontend/src/features/content/ItemEditorPage.test.tsx`, `ItemPreview.test.tsx` y `EditConflictDialog.test.tsx` (msw). Cubre:
  - los campos cambian según módulo y parte (la parte 1 de Inglés pide la clave entre las opciones del contexto; CE pide rúbrica);
  - los errores del cliente y del servidor aparecen junto al campo y se anuncian con `aria-live`;
  - el contador de palabras muestra "501/500";
  - la pestaña "Vista previa" muestra `ContentView` en un marco de 360 × 800 y la pestaña "Retroalimentación" la de cada opción;
  - un 412 abre el diálogo con "Tus cambios" y "Versión actual", con opciones de conservar o descartar;
  - con un ítem publicado, el editor avisa que se creará una versión nueva.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T055 [P] [US3] Prueba de componentes: `frontend/src/features/content/ContextEditorPage.test.tsx` y `MediaUpload.test.tsx`. Cubre:
  - aviso con el número de ítems que usan el contexto y cuántos están publicados, antes de confirmar;
  - texto alternativo obligatorio;
  - errores 413 y 415 legibles;
  - editor de opciones compartidas (de A a H) con retroalimentación.

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 3

- [ ] T056 [US3] Implementar `content/application/authoring.py` (crear, guardar borrador, enviar y comprobar duplicados) para que pase T049 → Qwen
  - Terminado: T049 en verde.
- [ ] T057 [US3] Implementar `content/application/contexts.py` (versionado y propagación a los ítems, FR-020) para que pase T050 → Qwen
  - Terminado: T050 en verde.
- [ ] T058 [US3] Implementar `content/infrastructure/images.py` (Pillow: firma, límites, re-codificación sin EXIF, SHA-256), `content/application/media.py` y `content/api/media_router.py`, con limitación de peticiones, para que pase T051 → Opus
  - Terminado: T051 en verde.
- [ ] T059 [US3] Implementar en `content/api/items_router.py` (`createItem`, `saveItemDraft`, `submitItem`, `getItemVersion` con diferencias) y `contexts_router.py` las operaciones de T052, con `content/application/queries/item_version_diff.py` → Qwen
  - Terminado: T052 en verde; las operaciones entran en la suite de T005.
- [ ] T060 [US3] Implementar `frontend/src/features/content/schemas.ts` para que pase T053 → Qwen
  - Terminado: T053 en verde.
- [ ] T061 [US3] Implementar `ItemEditorPage.tsx` (crear y editar), `ItemPreview.tsx`, `EditConflictDialog.tsx` e `ItemHistory.tsx` (versiones y diferencias) para que pase T054 → Qwen
  - Terminado: T054 en verde.
- [ ] T062 [US3] Implementar `ContextEditorPage.tsx` y `MediaUpload.tsx` para que pase T055 → Qwen
  - Terminado: T055 en verde.
- [ ] T063 [US3] E2E: `frontend/tests/e2e/content-authoring.spec.ts` con los escenarios B9 a B13 (incluida la edición simultánea en dos contextos de navegador) y axe en el editor y en la vista previa → Qwen
  - Terminado: en verde en Chromium y WebKit.
- [ ] T064 [US3] Revisión de US3 (Opus), anotada en `specs/002-banco-items/tasks.md`: versiones nuevas sobre lo publicado, propagación de contextos, imágenes, bloqueo optimista y fidelidad de la vista previa → Opus
  - Terminado: US3 aprobada.

**Checkpoint**: MVP del banco (US1 a US3): cargar, editar, revisar y publicar.

---

## Phase 6: User Story 4 - Importación de ítems nuevos en lote (Priority: P2)

**Goal**: importar desde JSON o XLSX con vista previa y reporte por ítem; confirmar todo o nada
con la declaración de originalidad.

**Independent Test**: subir la plantilla con 20 ítems válidos y 3 inválidos; ver la vista previa
y el reporte; confirmar; entran 20 (quickstart B14 y B15).

### Tests for User Story 4 ⚠️

- [ ] T065 [P] [US4] Prueba de seguridad: `backend/tests/unit/content/test_xlsx.py` (research R-04, FR-029). Cubre:
  - la plantilla generada tiene las hojas `items`, `instrucciones` y `listas` y validaciones de celda con los códigos activos;
  - una plantilla llena se lee como el formato v1;
  - varias filas con el mismo código de contexto lo comparten;
  - un texto distinto en una fila posterior responde `context_text_mismatch`;
  - una fila de Inglés parte 1 o de CE responde `unsupported_in_template`;
  - `.xlsm`, un ZIP sin `[Content_Types].xml`, más de 10 MB y un contenido descomprimido de más de 50 MB (bomba zip) se rechazan antes de abrir;
  - las fórmulas se leen como texto, sin evaluarse;
  - un XML con entidades externas es rechazado por defusedxml.

  → Opus
  - Terminado: la prueba falla.
- [ ] T066 [P] [US4] Prueba: `backend/tests/integration/content/test_bank_import_preview.py` (FR-030 a FR-033, FR-037). Cubre:
  - un archivo con 20 ítems válidos y 3 inválidos da 20 `create` y 3 `error` con `field`, `rule` y `message`;
  - un ítem igual a uno del banco con otro código da `duplicate_item`, y dos iguales en el mismo archivo, `duplicate_in_file`;
  - una referencia a un contexto inexistente da `context_unknown`;
  - el origen `ai` hace que `target_state` sea `in_review`;
  - más de 1 000 ítems responde `batch-too-large`;
  - un archivo ilegible o con otro esquema responde `unreadable-file`;
  - no se guarda ningún ítem; la importación queda `pending` con `expires_at` = creación + 24 h.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T067 [P] [US4] Prueba: `backend/tests/integration/content/test_bank_import_confirm.py` (FR-034 a FR-036). Cubre:
  - confirmar con `originality_declared` y `target_state` crea los válidos en una sola transacción;
  - un fallo inyectado a mitad no deja ninguno;
  - se guardan la declaración, `confirmed_at` y `result`;
  - cada ítem tiene el evento `imported` con `import_id`;
  - un ítem modificado por otra persona después de la vista previa queda omitido con `changed_since_preview`;
  - una importación ya confirmada o vencida responde `import-not-pending`;
  - sin válidos responde `nothing-to-import`;
  - `payload` queda NULL al confirmar.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T068 [P] [US4] Prueba: `backend/tests/integration/content/test_import_api.py`. Cubre:
  - `createImport` multipart con 201, 413, 415 y 422 según el contrato;
  - límite de 30 subidas por hora por usuario (429 con `Retry-After`);
  - `getImport` con filtro `action` y paginación;
  - `getImportReport` devuelve un XLSX con código, campo, regla y mensaje;
  - `confirmImport`;
  - `listImports`: el docente ve las suyas y el administrador, todas;
  - `getImportTemplate` devuelve un XLSX con `Content-Disposition`;
  - los logs no traen el nombre del archivo.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T069 [P] [US4] Prueba: `backend/tests/integration/content/test_import_tasks.py`. `purge_expired_imports` marca `expired` las pendientes vencidas y pone `payload` en NULL, sin tocar las confirmadas → Qwen
  - Terminado: la prueba falla.
- [ ] T070 [P] [US4] Prueba de componentes: `frontend/src/features/content/ImportPage.test.tsx` e `ImportPreviewPage.test.tsx`. Cubre:
  - subir un archivo y ver los conteos por acción;
  - tabla de errores filtrable con campo y regla legibles en español;
  - descargar el reporte y la plantilla;
  - "Confirmar" deshabilitado hasta marcar la declaración y elegir el estado;
  - un aviso si hay ítems de origen IA que entrarán En revisión;
  - el resultado final con creados y omitidos.

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 4

- [ ] T071 [US4] Implementar `content/infrastructure/interchange/xlsx_format.py` (lectura y escritura con openpyxl en `read_only` y `data_only`, defensas previas a abrir el archivo y uso de defusedxml) para que pase T065 → Qwen
  - Terminado: T065 en verde.
- [ ] T072 [US4] Implementar `content/domain/import_job.py` (`ImportRow` y acciones) y la parte de validación y vista previa de `content/application/bank_import.py`, para que pase T066 → Qwen
  - Terminado: T066 en verde.
- [ ] T073 [US4] Implementar la confirmación en `content/application/bank_import.py` para que pase T067 → Qwen
  - Terminado: T067 en verde.
- [ ] T074 [US4] Implementar en `content/api/transfer_router.py` `createImport`, `getImport`, `getImportReport`, `confirmImport`, `listImports` y `getImportTemplate`, con limitación de peticiones, para que pase T068 → Qwen
  - Terminado: T068 en verde; las operaciones entran en la suite de T005.
- [ ] T075 [US4] Implementar `content.purge_expired_imports` en `content/infrastructure/tasks.py` y programarla cada hora en `backend/src/saber_uli/worker.py`, para que pase T069 → Qwen
  - Terminado: T069 en verde.
- [ ] T076 [US4] Implementar `ImportPage.tsx` e `ImportPreviewPage.tsx` para que pase T070 → Qwen
  - Terminado: T070 en verde.
- [ ] T077 [US4] E2E: `frontend/tests/e2e/content-import.spec.ts` con los escenarios B14 y B15 y axe en la vista previa → Qwen
  - Terminado: en verde.
- [ ] T078 [US4] Revisión de US4 (Opus), anotada en `specs/002-banco-items/tasks.md`: defensas contra archivos maliciosos, transacción única, declaración de originalidad y límites → Opus
  - Terminado: US4 aprobada.

---

## Phase 7: User Story 5 - Actualización de ítems en lote con versiones (Priority: P2)

**Goal**: reimportar con códigos existentes crea versiones nuevas solo donde algo cambió, muestra
las diferencias y nunca duplica.

**Independent Test**: exportar 10 ítems publicados, cambiar 3, reimportar: solo 3 versiones
nuevas, con diferencias; reimportar el mismo archivo: 0 cambios (quickstart B16).

### Tests for User Story 5 ⚠️

- [ ] T079 [P] [US5] Prueba: `backend/tests/integration/content/test_bank_import_update.py` (FR-015, FR-016, FR-035, SC-002). Cubre:
  - un código existente con contenido cambiado da `update` con `changes` campo por campo;
  - un contenido idéntico (`content_hash`) da `unchanged`;
  - al confirmar: lo publicado crea la versión N+1 en el estado elegido y la publicada sigue vigente;
  - un Borrador o En revisión se actualiza en el lugar, sin versión nueva;
  - un ítem retirado crea una versión nueva y la historia conserva el retiro;
  - el importador queda en `contributor_ids`;
  - la misma importación repetida no crea versiones.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T080 [P] [US5] Prueba de componentes: `frontend/src/features/content/ImportPreviewPage.test.tsx` (casos de actualización) e `ItemHistory.test.tsx`. Cubre:
  - las filas `update` se despliegan con "antes" y "después" por campo;
  - "sin cambios" aparece agrupado;
  - la historia muestra cada versión con estado, autor, revisor, fechas y campos cambiados (FR-018).

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 5

- [ ] T081 [US5] Implementar en `content/application/bank_import.py` la acción `update`, con diferencias por campo (reutilizando `item_version_diff.py`), para que pase T079 → Qwen
  - Terminado: T079 en verde.
- [ ] T082 [US5] Implementar la vista de diferencias en `ImportPreviewPage.tsx` y completar `ItemHistory.tsx` para que pase T080 → Qwen
  - Terminado: T080 en verde.
- [ ] T083 [US5] E2E: agregar a `frontend/tests/e2e/content-import.spec.ts` el escenario B16 (exportar → cambiar → reimportar → 3 versiones → reimportar → 0 cambios) → Qwen
  - Terminado: en verde.
- [ ] T084 [US5] Revisión de US5 (Opus), anotada en `specs/002-banco-items/tasks.md`: idempotencia, diferencias y reglas de versiones → Opus
  - Terminado: US5 aprobada.

---

## Phase 8: User Story 6 - Exportación del banco (Priority: P2)

**Goal**: exportar el banco o un filtro en el formato de importación; reimportar lo exportado no
cambia nada.

**Independent Test**: exportar los ítems publicados de Inglés y reimportar el archivo: vista
previa con 0 cambios; en XLSX se informan los ítems de la parte 1 que quedaron fuera (quickstart
B17).

### Tests for User Story 6 ⚠️

- [ ] T085 [P] [US6] Prueba: `backend/tests/integration/content/test_bank_export.py` (FR-038, SC-008). Cubre:
  - JSON con los filtros `module`, `state`, `origin`, `difficulty` y `taxonomy_node`;
  - `version=published` frente a `latest`;
  - incluye los contextos usados, las categorías usadas y las rúbricas de las consignas;
  - reimportar lo exportado da 0 cambios;
  - XLSX con solo los ítems representables y `X-Skipped-Items` con el resto;
  - cada exportación queda en `content.exports`;
  - lectura por bloques de 500 (sin cargar todo en memoria).

  → Qwen
  - Terminado: la prueba falla.
- [ ] T086 [P] [US6] Prueba de componentes: `frontend/src/features/content/ExportPage.test.tsx`. Cubre los filtros, el formato, la versión y el aviso "N ítems no caben en la plantilla" a partir de `X-Skipped-Items` → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 6

- [ ] T087 [US6] Implementar `content/application/bank_export.py` y `exportItems` en `content/api/transfer_router.py` (respuesta en flujo con `Content-Disposition`) para que pase T085 → Qwen
  - Terminado: T085 en verde; la operación entra en la suite de T005.
- [ ] T088 [US6] Implementar `ExportPage.tsx` para que pase T086 → Qwen
  - Terminado: T086 en verde.
- [ ] T089 [US6] E2E: `frontend/tests/e2e/content-export.spec.ts` con el escenario B17 y la reimportación con 0 cambios → Qwen
  - Terminado: en verde.
- [ ] T090 [US6] Revisión de US6 (Opus), anotada en `specs/002-banco-items/tasks.md`: exportación con filtros, ida y vuelta sin cambios y escenario B17 → Opus
  - Terminado: US6 aprobada.

---

## Phase 9: User Story 7 - Cobertura del banco frente al examen (Priority: P3)

**Goal**: ver por módulo cuántos ítems hay por categoría frente al peso objetivo y cuántos faltan.

**Independent Test**: con algunos ítems publicados, abrir la cobertura de Inglés: cada parte con
sus publicados, En revisión, porcentaje, peso y "Faltan N" (quickstart B18).

### Tests for User Story 7 ⚠️

- [ ] T091 [P] [US7] Prueba: `backend/tests/integration/content/test_coverage.py` (FR-039, FR-040, R-16). Cubre:
  - la agrupación por el tipo de categoría que tiene pesos: LC por afirmación, RC y CC por competencia e Inglés por parte (research R-16);
  - `published`, `in_review` y `published_share`;
  - `missing = max(0, ceil(bank_target × target_weight) − published)` y `below_target`;
  - los ítems retirados no cuentan;
  - CE (sin pesos) informa solo los totales.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T092 [P] [US7] Prueba de componentes: `frontend/src/features/content/CoveragePage.test.tsx`. Cubre:
  - la tabla por categoría con "Faltan N" en texto (no solo color) y orden por faltantes;
  - cada categoría enlaza a `/banco` filtrado por ella;
  - axe sin violaciones.

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 7

- [ ] T093 [US7] Implementar `content/application/coverage.py` y `getModuleCoverage` en `content/api/insights_router.py` para que pase T091 → Qwen
  - Terminado: T091 en verde; la operación entra en la suite de T005.
- [ ] T094 [US7] Implementar `CoveragePage.tsx` para que pase T092 → Qwen
  - Terminado: T092 en verde.
- [ ] T095 [US7] Revisión de US7 (Opus), anotada en `specs/002-banco-items/tasks.md`, con el escenario B18 → Opus
  - Terminado: US7 aprobada.

---

## Phase 10: User Story 8 - Estadísticas de cada ítem publicado (Priority: P3)

**Goal**: por versión publicada, acierto, opciones elegidas y discriminación, con "datos
insuficientes" por debajo de 30 respuestas y filtro de señales de problema.

**Independent Test**: con una fuente de respuestas de prueba, comprobar las cifras de una versión
y que una versión nueva empieza en cero; sin datos, "aún no hay datos suficientes" (quickstart
B19).

### Tests for User Story 8 ⚠️

- [ ] T096 [P] [US8] Prueba: `backend/tests/unit/content/test_statistics.py` (FR-041 a FR-043, R-13). Con datos sintéticos de resultado conocido:
  - porcentaje de acierto y porcentaje por opción;
  - punto-biserial corregida contra el puntaje del resto, comparada con un cálculo de referencia con tolerancia de 1e-6;
  - menos de 30 primeras respuestas da `sufficient_data = false` y cifras nulas;
  - señales `too_easy` (> 0.9), `too_hard` (< 0.2), `negative_discrimination` (< 0) y `distractor_beats_key`;
  - varianza cero devuelve discriminación nula sin error.

  → Opus
  - Terminado: la prueba falla.
- [ ] T097 [P] [US8] Prueba: `backend/tests/integration/content/test_statistics_refresh.py`. Cubre:
  - con una `ResponseStatisticsSource` falsa, `refresh_item_statistics` reemplaza `content.item_version_stats` por versión;
  - la fuente nula de 002 deja todo en "datos insuficientes";
  - `listItems?signal=too_hard` filtra;
  - `getItemStatistics` lista las versiones publicadas y retiradas, y una versión nueva aparece con 0 respuestas;
  - la respuesta no contiene identificadores de estudiantes (FR-044).

  → Qwen
  - Terminado: la prueba falla.
- [ ] T098 [P] [US8] Prueba de componentes: `frontend/src/features/content/ItemStatistics.test.tsx`. Cubre:
  - el mensaje "Aún no hay datos suficientes" con el número de respuestas;
  - las cifras con formato es-CO;
  - las señales con texto explicativo;
  - las barras por opción con su valor en texto (accesibles).

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 8

- [ ] T099 [US8] Implementar `content/domain/statistics.py` para que pase T096 → Qwen
  - Terminado: T096 en verde.
- [ ] T100 [US8] Implementar `content/application/statistics_refresh.py`, `content/infrastructure/null_statistics_source.py`, la tarea `content.refresh_item_statistics` (diaria, 03:00 America/Bogota, en `worker.py`), el filtro `signal` en `list_items.py` y `getItemStatistics` en `insights_router.py`, para que pase T097 → Qwen
  - Terminado: T097 en verde; la operación entra en la suite de T005.
- [ ] T101 [US8] Implementar `ItemStatistics.tsx` (pestaña del editor) y el filtro de señales en `BankPage.tsx` para que pase T098 → Qwen
  - Terminado: T098 en verde.
- [ ] T102 [US8] Revisión de US8 (Opus), anotada en `specs/002-banco-items/tasks.md`: fórmula, umbrales y agregación sin identificadores → Opus
  - Terminado: US8 aprobada.

---

## Phase 11: User Story 9 - Mantenimiento de la taxonomía (Priority: P3)

**Goal**: el administrador mantiene categorías, pesos, metas y rúbricas como datos; lo que está en
uso solo se desactiva.

**Independent Test**: crear una evidencia, usarla en un ítem, intentar borrarla (409) y
desactivarla; un docente no puede cambiar la taxonomía (quickstart B20).

### Tests for User Story 9 ⚠️

- [ ] T103 [P] [US9] Prueba: `backend/tests/integration/content/test_taxonomy_admin.py` (FR-001, FR-040, FR-045). Cubre:
  - crear una categoría con el padre del tipo correcto (evidencia → afirmación → competencia); `code` repetido responde `taxonomy-code-taken`;
  - editar el nombre, la descripción o `target_weight`, con `warnings` si la suma del tipo en el módulo queda fuera de [0.95, 1.05];
  - desactivar y reactivar;
  - borrar una categoría en uso o con hijas responde `taxonomy-node-in-use`; borrar una sin uso funciona;
  - `updateContentModule.bank_target`;
  - crear y editar una rúbrica (dimensiones con al menos 2 niveles);
  - cada cambio deja una fila en `content.taxonomy_changes` con `before` y `after`;
  - las rutas responden 403 a un docente.

  → Qwen
  - Terminado: la prueba falla.
- [ ] T104 [P] [US9] Prueba de componentes: `frontend/src/features/content/TaxonomyPage.test.tsx`. Cubre:
  - el árbol por módulo y tipo;
  - editar el peso con el aviso de la suma;
  - "Desactivar" en lugar de "Borrar" cuando `in_use`;
  - el editor de rúbricas;
  - axe sin violaciones.

  → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 9

- [ ] T105 [US9] Implementar `content/application/taxonomy_admin.py`, `rubrics.py` y `content/api/taxonomy_router.py` (`listContentModules`, `updateContentModule`, `createTaxonomyNode`, `updateTaxonomyNode`, `deleteTaxonomyNode`, `listRubrics`, `createRubric`, `updateRubric`) para que pase T103 → Qwen
  - Terminado: T103 en verde; las operaciones entran en la suite de T005.
- [ ] T106 [US9] Implementar `TaxonomyPage.tsx` para que pase T104 → Qwen
  - Terminado: T104 en verde.
- [ ] T107 [US9] E2E: `frontend/tests/e2e/content-taxonomy.spec.ts` con el escenario B20 → Qwen
  - Terminado: en verde.
- [ ] T108 [US9] Revisión de US9 (Opus), anotada en `specs/002-banco-items/tasks.md`: jerarquía, desactivación, permisos y escenario B20 → Opus
  - Terminado: US9 aprobada.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Mis datos, rendimiento, contrato completo, seguridad, documentación y validación de
punta a punta.

- [ ] T109 [P] Prueba e implementación de la sección `banco_de_items` de "Mis datos". La prueba va en `backend/tests/integration/content/test_data_export.py`: lista los códigos de los ítems y versiones que la persona creó, modificó o revisó, sin contenido de otras personas. La implementación va en `content/application/data_export.py`, registrada en `DataExportRegistry` desde `main.py` (FR-031 de 001, research R-14) → Qwen
  - Terminado: prueba en verde; `GET /api/v1/me/data-export` incluye la sección.
- [ ] T110 [P] Prueba de rendimiento: `backend/tests/integration/content/test_performance_budgets.py` (SC-003, SC-004, SC-009, SC-010, R-18). Siembra 10 000 ítems con la marca `carga-002-` y mide:
  - vista previa y confirmación de 500 ítems;
  - `listItems` con búsqueda y filtros;
  - cobertura;
  - estadísticas;
  - exportación completa.

  Registra los tiempos y los exige solo con `PERF_BUDGETS_ENFORCE=1` → Qwen
  - Terminado: corre en CI sin exigir; los tiempos quedan anotados en esta tarea.
- [ ] T111 Ajustar índices o consultas de `backend/migrations/versions/` y `content/application/queries/` si T110 supera las metas (con `EXPLAIN ANALYZE`) y registrar las mediciones en `specs/002-banco-items/tasks.md` → Opus
  - Terminado: metas cumplidas en local o decisión pendiente registrada con datos para el servidor de referencia.
- [ ] T112 Completar la suite de contrato de T005: las 35 operaciones de `specs/002-banco-items/contracts/openapi.yaml` implementadas y sin fallos de Schemathesis; la verificación de `main.py` no reporta operaciones faltantes → Opus
  - Terminado: `uv run pytest tests/contract` en verde con las dos suites.
- [ ] T113 [P] Prueba de logs sin datos personales: `backend/tests/integration/content/test_content_logs.py` captura los logs de la carga, la importación (incluido el nombre del archivo), la revisión y la exportación, y comprueba que no hay textos de ítems, nombres, correos ni nombres de archivo (principio V) → Opus
  - Terminado: prueba en verde.
- [ ] T114 [P] Agregar `/banco`, `/banco/items/nuevo` (con la vista previa abierta), `/banco/importaciones/$id` y `/banco/cobertura` al recorrido de accesibilidad de `frontend/tests/e2e/a11y.spec.ts`, y comprobar en el viewport móvil que no hay desplazamiento horizontal → Qwen
  - Terminado: axe sin violaciones en Chromium y WebKit.
- [ ] T115 Revisión ASVS 4.0.3 nivel 2 de la funcionalidad en `docs/security/asvs-002-banco-items.md`: V5 (Markdown, salida), V12 (archivos: XLSX, JSON e imágenes), V4 (permisos y autoaprobación), V7 (logs) y V13 (API) → Opus
  - Terminado: documento sin hallazgos abiertos o con su plan.
- [ ] T116 [P] Documentación:
  - `README.md`: el banco y cómo cargarlo;
  - `specs/002-banco-items/quickstart.md`: cualquier diferencia encontrada;
  - `docs/SABER_ULI_KIT_SDD.md` §8.2: que la validación usa `backend/schemas/banco_items.schema.json`.

  → Qwen
  - Terminado: los comandos de los documentos funcionan tal como están escritos.
- [ ] T117 Validación de punta a punta, anotada en `specs/002-banco-items/tasks.md`:
  - escenarios B1 a B23 del quickstart sobre `docker compose up` desde cero;
  - cobertura ≥ 80 % en `content.domain` y `content.application`;
  - CI en verde en el PR;
  - `/speckit.analyze` sin inconsistencias abiertas;
  - Definición de Terminado del kit (sección 9), incluida la carga del banco inicial;
  - SC-007: un docente que no conoce la aplicación crea un ítem completo con contexto, lo previsualiza y lo envía a revisión en menos de 10 minutos; prueba manual cronometrada, con el tiempo anotado.

  → Opus
  - Terminado: todo lo anterior comprobado y anotado bajo esta tarea.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias. T005 depende de T003; T006 y T007–T008 son independientes.
- **Foundational (fase 2)**: depende de la fase 1 y **bloquea todas las historias**. T035 (revisión
  de seguridad) cierra la fase.
- **Historias (fases 3 a 11)**: dependen de la fase 2. Orden recomendado: US1 → US2 → US3 (P1, MVP)
  → US4 → US5 → US6 (P2) → US7 → US8 → US9 (P3).
- **Polish (fase 12)**: depende de las historias que se entreguen; T112 y T117 requieren todas.

### User Story Dependencies

| Historia | Depende de | Nota de independencia |
|----------|------------|-----------------------|
| US1 | Fase 2 | Ninguna otra historia |
| US2 | Fase 2 | Sus pruebas crean ítems En revisión con fábricas; en el despliegue usa los del banco inicial (US1) |
| US3 | Fase 2 | La revisión de lo creado se prueba en US2; aquí basta con enviar a revisión |
| US4 | Fase 2 | Reutiliza el validador del dominio; no necesita la interfaz de US3 |
| US5 | US4 (T072–T073) | Extiende la importación con la acción `update` |
| US6 | Fase 2 | Su prueba de ida y vuelta usa la importación de US4 si existe; si no, compara contra el lector de T026 |
| US7 | Fase 2 | Los ítems publicados se crean con fábricas |
| US8 | Fase 2 | Usa una fuente de respuestas falsa; la real llega con 003 |
| US9 | Fase 2 | Ninguna otra historia |

### Within Each User Story

- Las pruebas se escriben primero y deben fallar (principio IV).
- Dominio → aplicación → API → frontend → e2e → revisión de Opus.
- Una historia se cierra cuando su tarea de revisión está aprobada.

### Parallel Opportunities

- Fase 1: T002, T004, T006 y T007 en paralelo tras T001 y T003.
- Fase 2: todas las pruebas [P] (T009, T011, T013, T015, T017, T019, T021, T023, T025, T027, T031,
  T033) en paralelo; cada implementación sigue a su prueba. El frontend (T031–T034) avanza en
  paralelo con el backend.
- Tras la fase 2: US1, US2, US3, US4, US7, US8 y US9 pueden avanzar en paralelo; US5 espera a US4.
- Dentro de cada historia: todas las pruebas [P] en paralelo.

---

## Parallel Example: User Story 3

```bash
# Pruebas de US3 en paralelo (primero; deben fallar):
Task: "T049 Prueba de autoría en backend/tests/integration/content/test_authoring.py"            # Qwen
Task: "T050 Prueba de contextos en backend/tests/integration/content/test_contexts.py"           # Qwen
Task: "T051 Prueba de imágenes en backend/tests/integration/content/test_media.py"              # Opus
Task: "T052 Prueba de la API en backend/tests/integration/content/test_items_api_authoring.py"  # Qwen
Task: "T053 Prueba de esquemas zod en frontend/src/features/content/schemas.test.ts"            # Qwen
Task: "T054 Prueba del editor en frontend/src/features/content/ItemEditorPage.test.tsx"         # Qwen
Task: "T055 Prueba del editor de contextos en frontend/src/features/content/ContextEditorPage.test.tsx"  # Qwen

# Luego, implementaciones en paralelo entre backend y frontend:
Task: "T056 Authoring" + Task: "T057 Contexts" + Task: "T058 Imágenes" + Task: "T060 schemas.ts"
```

## Parallel Example: User Story 4

```bash
Task: "T065 Prueba XLSX"  +  Task: "T066 Prueba vista previa"  +  Task: "T067 Prueba confirmación"
Task: "T068 Prueba API"   +  Task: "T069 Prueba purga"        +  Task: "T070 Prueba de pantallas"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Fase 1: Setup.
2. Fase 2: Foundational (incluye la revisión de seguridad T035).
3. Fases 3–5: US1, US2 y US3.
4. **Parar y validar**: quickstart B1 a B13. El banco inicial queda cargado, los administradores
   lo revisan y publican, y los docentes corrigen y crean ítems. Es el mínimo para que la
   spec 003 entregue la primera práctica con ítems publicados.

### Incremental Delivery

1. MVP del banco (US1–US3) → demo y revisión del banco inicial por los docentes.
2. Crecimiento en lote (US4 + US5 + US6) → demo.
3. Gestión del banco (US7 + US9) → demo.
4. Estadísticas (US8) → se completan con datos cuando llegue 003.
5. Polish (fase 12) → Definición de Terminado.

### Reparto entre modelos

| Modelo | Tareas | Total |
|--------|--------|-------|
| Opus (diseño, seguridad, revisión) | T005, T006, T009, T011, T012, T021, T022, T029, T035, T036, T040, T041, T048, T051, T058, T064, T065, T078, T084, T090, T095, T096, T102, T108, T111, T112, T113, T115, T117 | 29 |
| Qwen (implementación) | Todas las demás | 88 |

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Las etiquetas [USn] permiten rastrear cada tarea a su historia.
- Verificar que cada prueba falla antes de implementar.
- Un commit por tarea (Conventional Commits: `feat(content): …`, `test(content): …`).
- Trazabilidad de requisitos:

  | Requisitos | Tareas |
  |------------|--------|
  | FR-001…FR-009 | T013–T018, T050–T051, T103 |
  | FR-010…FR-020 | T021, T041, T049–T050, T079 |
  | FR-021…FR-023 | T036–T039 |
  | FR-024…FR-027 | T049–T055 |
  | FR-028…FR-038 | T065–T070, T079, T085 |
  | FR-039…FR-044 | T091, T096–T098 |
  | FR-045…FR-047 | T011, T029, T103, T113 |
  | SC-001…SC-002 | T036, T079 |
  | SC-003, SC-004, SC-009, SC-010 | T110 |
  | SC-005 | T041 |
  | SC-006 | T009, T023 |
  | SC-007 | T063, T117 (prueba manual cronometrada) |
  | SC-008 | T085 |
