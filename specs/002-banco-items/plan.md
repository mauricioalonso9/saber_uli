# Implementation Plan: Banco de ítems: carga inicial, importación, actualización y revisión

**Branch**: `002-banco-items` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-banco-items/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

La funcionalidad 002 crea el banco de ítems de Saber Uli en un contexto nuevo, `content`, con su
propio esquema de PostgreSQL.

- **Taxonomía como datos**: módulos, categorías del ICFES, rúbricas y distribución objetivo.
- **Ítems y contextos con versiones inmutables**: a lo sumo una versión publicada y una abierta
  por ítem.
- **Flujo de revisión**: solo los administradores aprueban, y nunca una versión que crearon o
  modificaron.
- **Un único formato de intercambio**: el JSON del banco inicial, con su JSON Schema generado,
  sirve para la carga en cada despliegue, la importación en dos pasos (vista previa y
  confirmación) y la exportación. Tiene además una plantilla XLSX para ítems de selección.
- **Huellas de contenido**: hacen idempotentes las recargas y reimportaciones y detectan
  duplicados.
- **Interfaz**: la PWA suma el banco (`/banco`) con editor, vista previa móvil fiel (componente
  `ContentView`, que reutilizará 003), cola de revisión, importación y exportación, cobertura y
  estadísticas. También suma la taxonomía en `/admin/taxonomia`.
- **Estadísticas**: quedan definidas con su fórmula y su interfaz. Los datos llegan con la
  práctica (003).

Sobre la base de 001 se agregan:

- tres permisos (`content:author`, `content:review` y `content:taxonomy_manage`);
- un método en la fachada de `identity` (`display_names`);
- el comando `saber-uli content load-seed`, que ejecuta `migrate`.

El detalle está en [research.md](./research.md) (R-01 a R-18) y en el ADR 0008.

## Technical Context

**Language/Version**: Python 3.13 (backend); TypeScript 6 sobre Node.js 24 LTS (frontend)

**Primary Dependencies**:

- Base de 001: FastAPI, Pydantic v2, SQLAlchemy 2 asíncrono + asyncpg, Alembic, Celery + Beat,
  structlog; React, TanStack Router y Query, react-hook-form + zod, orval, react-markdown.
- Nuevas en backend: python-multipart, openpyxl + defusedxml y Pillow (R-04, R-05, R-11).
- Nuevas en frontend: remark-gfm, remark-math y rehype-katex (R-10).

**Storage**: PostgreSQL 18, esquema nuevo `content`:

- tablas de taxonomía, contextos, ítems, versiones, historia, importaciones, exportaciones,
  cargas del banco inicial, estadísticas e imágenes (`bytea`);
- índice GIN de texto completo `spanish`.

Sin cambios en Redis (solo los contadores de limitación de peticiones de 001).

**Testing**:

- **Base de 001**: pytest + Testcontainers (`postgres:18`), Schemathesis (segunda suite para el
  contrato de 002), import-linter con el contexto `content`, Vitest + MSW, y Playwright + axe.
- **Pruebas nuevas**:
  - esquema de intercambio generado frente al versionado;
  - metas de rendimiento con 500 y 10 000 ítems (R-18);
  - permisos de la base en `content` (infraestructura).

**Target Platform**: la de 001. Las pantallas del banco se usan sobre todo en escritorio, pero
deben funcionar en el viewport móvil (Definición de Terminado).

**Project Type**: aplicación web (API REST + PWA) en monorepo, como en 001

**Performance Goals**:

- vista previa de 500 ítems en menos de 30 s (SC-004);
- confirmar 500 ítems en menos de 1 minuto (SC-003);
- búsqueda, filtros, cobertura y estadísticas con 10 000 ítems en menos de 2 s (SC-009);
- exportación completa en menos de 1 minuto (SC-010);
- p95 por debajo de 300 ms en lecturas simples, como en 001.

**Constraints**:

- archivos de máximo 10 MB y 1 000 ítems;
- imágenes de máximo 1 MB, sin SVG y re-codificadas sin EXIF;
- contenido Markdown sin HTML crudo;
- sin datos personales en logs ni en el outbox;
- historia e importaciones sin `UPDATE` ni `DELETE` para el rol de la aplicación (salvo las
  columnas de estado de `imports`);
- WCAG 2.2 AA, incluidas las fórmulas, con MathML.

**Scale/Scope**:

- hasta 10 000 ítems, con decenas de docentes y administradores editando y pocas importaciones
  concurrentes;
- 9 historias de usuario;
- 35 operaciones de API en 29 rutas (contrato de 002);
- alrededor de 11 pantallas nuevas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principio | Cómo lo cumple este plan | Pre | Post |
|---|-----------|--------------------------|-----|------|
| I | Especificación primero | `spec.md` con 5 aclaraciones registradas; el plan no agrega comportamiento fuera de la spec (los límites de archivo y el umbral de 30 respuestas vienen de supuestos documentados) | ✅ | ✅ |
| II | Monolito modular DDD | Contexto nuevo `content` con capas hexagonales y esquema propio; usa `identity` solo por su fachada (`display_names`, usuario autenticado y permisos); historia y auditoría dentro de su esquema, sin escribir en `identity`; `import-linter` con el contexto nuevo (R-01, R-14) | ✅ | ✅ |
| III | Contrato primero | `contracts/openapi.yaml` (OpenAPI 3.1, validado con openapi-spec-validator y cargado en Schemathesis: 35 operaciones) antes de implementar; cliente orval en `src/api/content`; los permisos nuevos amplían el enum de 001 sin romper `/api/v1` (R-15) | ✅ | ✅ |
| IV | Pruebas primero (TDD) | Pirámide completa: dominio (validación por módulo y parte, conteo de palabras, máquina de estados, huellas, estadísticas), integración con Postgres 18 real (índices parciales, transacción única, idempotencia, permisos), contrato, e2e con axe; esquema de intercambio verificado; cobertura ≥ 80 % en `content.domain` y `content.application` | ✅ | ✅ |
| V | Protección de datos | `content` guarda solo UUID de personas (los nombres los da `identity`); sección `banco_de_items` en "Mis datos"; estadísticas agregadas sin identificador; EXIF eliminado de imágenes; logs solo con códigos y conteos (R-11, R-13, R-14) | ✅ | ✅ |
| VI | Integridad académica | Revisión humana obligatoria antes de publicar; autoaprobación imposible; confirmaciones del revisor y declaración de originalidad registradas; origen `ia` visible y forzado a En revisión; taxonomía del ICFES como datos (R-07, R-08) | ✅ | ✅ |
| VII | Gamificación al servicio del aprendizaje | Retroalimentación obligatoria en cada opción y explicación general en cada ítem (FR-006), condición para que 003 la muestre en cada respuesta | ✅ | ✅ |
| VIII | Móvil primero, accesible | Vista previa en marco de 360 × 800 con el mismo componente que verá el estudiante; fórmulas con MathML; texto alternativo obligatorio; cobertura sin depender del color; axe en e2e (R-10, R-17) | ✅ | ✅ |
| IX | Seguridad por diseño | Permisos que niegan por defecto; sesión privilegiada en todas las funciones de gestión; Markdown sin HTML crudo; imágenes verificadas y re-codificadas, sin SVG; XLSX con defusedxml y límites contra bombas zip; limitación de subidas; Trivy en CI (R-04, R-08, R-10, R-11) | ✅ | ✅ |
| X | Reproducibilidad (12-factor) | `docker compose up` carga el banco inicial de forma idempotente con *advisory lock*; si el archivo es inválido, `migrate` falla y no arranca un banco a medias; migración Alembic para el esquema y los permisos (R-07) | ✅ | ✅ |
| XI | Simplicidad | Importación síncrona sin colas nuevas; imágenes en la base sin volumen ni servicio; texto completo nativo sin extensiones; JSON Schema generado sin librería adicional; cada dependencia nueva justificada (R-04, R-05, R-11, R-12); ADR 0008 | ✅ | ✅ |

**Resultado**: la puerta pasa sin excepciones. No hay entradas en *Complexity Tracking*.

## Project Structure

### Documentation (this feature)

```text
specs/002-banco-items/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R-01 a R-18 y dependencias nuevas
├── data-model.md        # Fase 1: esquema content, estados, historia, formato de intercambio
├── quickstart.md        # Fase 1: levantar con el banco cargado y escenarios B1 a B23
├── contracts/
│   └── openapi.yaml     # Fase 1: contrato OpenAPI 3.1 (35 operaciones)
├── checklists/
│   └── requirements.md  # Lista de calidad de la especificación
└── tasks.md             # Fase 2 (/speckit-tasks; no lo crea este comando)
```

### Source Code (repository root)

Solo se listan los archivos y directorios nuevos o modificados. El resto es igual a
[001/plan.md](../001-identidad-acceso/plan.md).

```text
saber-uli/
├── backend/
│   ├── pyproject.toml                      # + python-multipart, openpyxl, defusedxml, pillow
│   ├── .importlinter                       # + saber_uli.content en los cinco contratos
│   ├── schemas/
│   │   └── banco_items.schema.json         # NUEVO: JSON Schema generado del formato v1 (R-03)
│   ├── src/saber_uli/
│   │   ├── main.py                         # + routers y servicios de content; unión de contratos
│   │   ├── cli.py                          # + `content load-seed [--file]`
│   │   ├── worker.py                       # + Beat: purga de importaciones vencidas,
│   │   │                                   #   recálculo nocturno de estadísticas
│   │   ├── identity/
│   │   │   ├── domain/permissions.py       # + content:author, content:review, content:taxonomy_manage
│   │   │   └── application/public.py       # + UserDirectory.display_names(ids)
│   │   └── content/                        # NUEVO contexto (R-01)
│   │       ├── domain/
│   │       │   ├── module.py  taxonomy.py  rubric.py         # Module, TaxonomyNode, reglas por módulo y parte
│   │       │   ├── context.py  item.py  item_version.py      # agregados, validación por tipo
│   │       │   ├── lifecycle.py                              # máquina de estados y autoaprobación
│   │       │   ├── word_count.py  fingerprint.py             # R-10, R-06
│   │       │   ├── statistics.py                             # punto-biserial corregida, señales (R-13)
│   │       │   ├── import_job.py                             # resultado por fila, acciones
│   │       │   └── events.py  errors.py
│   │       ├── application/
│   │       │   ├── ports.py  unit_of_work.py                 # repositorios, MediaProcessor, ResponseStatisticsSource
│   │       │   ├── taxonomy_admin.py  rubrics.py
│   │       │   ├── contexts.py  media.py
│   │       │   ├── authoring.py                              # crear, guardar borrador, enviar, comentar
│   │       │   ├── review.py                                 # aprobar, devolver, rechazar, retirar
│   │       │   ├── bank_import.py                            # validar → vista previa → confirmar (R-05)
│   │       │   ├── seed_loader.py                            # carga idempotente del banco inicial (R-07)
│   │       │   ├── bank_export.py  coverage.py  statistics_refresh.py
│   │       │   ├── queries/                                  # listado, historia, versión con diferencias
│   │       │   ├── data_export.py                            # sección "banco_de_items" de Mis datos
│   │       │   └── public.py                                 # fachada (versiones publicadas para 003)
│   │       ├── infrastructure/
│   │       │   ├── orm.py  repositories/  unit_of_work.py
│   │       │   ├── interchange/                              # modelos Pydantic del formato v1, lector JSON,
│   │       │   │                                             # lector/escritor XLSX (openpyxl), generador del schema
│   │       │   ├── images.py                                 # Pillow: verificación y re-codificación
│   │       │   ├── null_statistics_source.py                 # fuente vacía hasta 003
│   │       │   └── tasks.py                                  # tareas Celery
│   │       └── api/
│   │           ├── taxonomy_router.py  contexts_router.py  media_router.py
│   │           ├── items_router.py  review_router.py
│   │           ├── transfer_router.py  insights_router.py
│   │           └── etag.py                                   # ETag / If-Match (R-09)
│   ├── migrations/versions/
│   │   ├── 0008_content_schema.py          # esquema, tablas, índices, CHECK
│   │   └── 0009_content_grants.py          # permisos de saber_app (data-model §2.14)
│   └── tests/
│       ├── unit/content/                   # dominio, interchange, XLSX, estadísticas
│       ├── integration/content/            # repositorios, casos de uso, carga, rendimiento
│       ├── contract/test_content_contract.py
│       └── infra/                          # + permisos del esquema content
├── frontend/
│   ├── package.json                        # + remark-gfm, remark-math, rehype-katex
│   ├── orval.config.ts                     # + destino content
│   ├── src/
│   │   ├── api/content/                    # GENERADO por orval
│   │   ├── app/router.tsx                  # + rutas /banco/* y /admin/taxonomia (bajo demanda)
│   │   ├── shared/content/                 # ContentView, MarkdownView (gfm + KaTeX)
│   │   └── features/content/
│   │       ├── BankPage.tsx  ReviewQueuePage.tsx
│   │       ├── ItemEditorPage.tsx  ItemPreview.tsx  ItemHistory.tsx  EditConflictDialog.tsx
│   │       ├── ContextEditorPage.tsx  MediaUpload.tsx
│   │       ├── ImportPage.tsx  ImportPreviewPage.tsx  ExportPage.tsx
│   │       ├── CoveragePage.tsx  ItemStatistics.tsx
│   │       ├── TaxonomyPage.tsx                              # /admin/taxonomia
│   │       └── schemas.ts                                    # zod con las reglas del dominio
│   └── tests/
│       ├── unit/ (junto a cada componente)
│       └── e2e/content-*.spec.ts           # revisión, importación, vista previa, axe
└── docs/adr/0008-banco-items-versiones-e-intercambio.md
```

**Structure Decision**:

- **Backend**: se agrega el contexto `content` siguiendo el patrón de `identity`, con fachada
  pública, unidad de trabajo y repositorios como puertos.
- **Frontend**: se agrega la funcionalidad `content`. El componente de presentación del contenido
  vive en `shared/content`, porque lo usarán la vista previa (002) y la práctica (003).
- **Contrato**: tiene su propio archivo (R-15).
- **Carga del banco inicial**: queda en el servicio `migrate`, después de Alembic.

### Servicios de Docker Compose

No hay servicios nuevos. Cambian dos:

| Servicio | Cambio |
|----------|--------|
| `migrate` | Después de `alembic upgrade head` ejecuta `saber-uli content load-seed`; si falla, el despliegue se detiene (R-07) |
| `beat` | Programa `content.purge_expired_imports` (cada hora) y `content.refresh_item_statistics` (diaria, 03:00 America/Bogota) |

### Mapa de historias de usuario a componentes

| Historia | Backend (`content`) | Frontend | Contrato |
|----------|---------------------|----------|----------|
| US1 Carga del banco inicial | `SeedLoader`, `interchange`, CLI `content load-seed` | — (resumen en logs y `seed_loads`) | — |
| US2 Revisión y publicación | `Review` (aprobar, devolver, rechazar, retirar), `lifecycle` | `ReviewQueuePage`, acciones en `ItemEditorPage` | `approveItem`, `returnItem`, `rejectItem`, `retireItem`, `commentItem`, `listItems?awaiting_my_review` |
| US3 Crear, editar y previsualizar | `Authoring`, `Contexts`, `Media`, validación del dominio | `ItemEditorPage`, `ContextEditorPage`, `ItemPreview`, `ContentView`, `EditConflictDialog` | `createItem`, `getItem`, `saveItemDraft`, `submitItem`, `*Context`, `*ContentMedia` |
| US4 Importación de nuevos | `BankImport` (validar, vista previa, confirmar), lector JSON y XLSX | `ImportPage`, `ImportPreviewPage` | `getImportTemplate`, `createImport`, `getImport`, `getImportReport`, `confirmImport`, `listImports` |
| US5 Actualización con versiones | `BankImport` (acción `update`, diferencias), consultas de historia | `ImportPreviewPage`, `ItemHistory` | `getItemHistory`, `getItemVersion` |
| US6 Exportación | `BankExport` | `ExportPage` | `exportItems` |
| US7 Cobertura | `Coverage` | `CoveragePage` | `getModuleCoverage` |
| US8 Estadísticas | `statistics` (dominio), `StatisticsRefresh`, puerto `ResponseStatisticsSource` | `ItemStatistics`, filtro de señales en `BankPage` | `getItemStatistics`, `listItems?signal` |
| US9 Taxonomía | `TaxonomyAdmin`, `Rubrics` | `TaxonomyPage` | `listContentModules`, `updateContentModule`, `*TaxonomyNode`, `*Rubric` |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Sin violaciones que justificar.

## Riesgos y dependencias externas

| Riesgo o dependencia | Impacto | Mitigación |
|----------------------|---------|------------|
| Se necesitan al menos dos administradores para revisar lo que un administrador modificó (aclaración FR-013) | Ítems bloqueados En revisión si hay un solo administrador | La cola marca `needs_another_reviewer`; quickstart pide dos administradores; documentarlo para la universidad |
| Revisión del banco inicial por docentes de cada área (constitución VI) | Sin ella no hay ítems publicados para 003 | La cola de revisión filtra por módulo; el banco inicial queda En revisión desde el primer despliegue |
| Taxonomía parafraseada del ICFES (`fuente_taxonomia` del banco inicial) | Etiquetas desalineadas con la guía oficial | La taxonomía es editable (US9); el revisor confirma la alineación al aprobar (FR-014) |
| Estadísticas sin datos hasta 003 | US8 se entrega sin cifras reales | Fórmula probada con datos sintéticos; puerto listo para 003 |
| Metas de rendimiento medidas en runners compartidos | Pruebas intermitentes | Se miden siempre y se exigen con `PERF_BUDGETS_ENFORCE=1` en el servidor de referencia, junto con la medición pendiente de 001/T176 (R-18) |

## Notas de ejecución

- Rama: `002-banco-items`, creada desde `main` después de fusionar 001 y la actualización de
  dependencias.
- El orden sugerido para `/speckit-tasks`:
  1. fundaciones: esquema, permisos, contrato, orval e import-linter;
  2. US1 (carga), que habilita los datos reales para las demás;
  3. US3 y US2, el MVP de revisión;
  4. US4, US5 y US6;
  5. US7, US8 y US9.
- Siguiente paso: `/speckit-tasks`.
