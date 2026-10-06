---
description: "Tareas de implementación de 001-identidad-acceso"
---

# Tasks: Identidad, acceso institucional e invitados

**Input**: Documentos de diseño en `specs/001-identidad-acceso/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml),
[quickstart.md](./quickstart.md)

**Tests**: Obligatorias (constitución, principio IV: TDD no negociable). Cada tarea de prueba se
escribe primero y **debe fallar** antes de empezar la tarea de implementación que la sigue.

**Organization**: Tareas agrupadas por historia de usuario; cada historia se entrega y se prueba
de forma independiente a partir de la fase 2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: Historia de usuario de `spec.md` (US1…US8).
- Cada tarea indica los archivos que toca, su criterio de **Terminado** y a quién se **asigna**.

## Convenciones de trabajo (dos modelos)

- **→ Qwen**: implementación bien definida. Qwen ejecuta la tarea con `/speckit.implement`,
  escribe primero la prueba y confirma que falla, implementa lo mínimo, ejecuta la suite del
  contexto, hace un commit por tarea (Conventional Commits) y agrega bajo la tarea la línea
  `- Estado: lista para revisión`. **No marca la casilla**. No cambia `contracts/openapi.yaml`,
  `data-model.md` ni los ADR: si algo no encaja, agrega `- Decisión pendiente: …` y sigue.
- **→ Opus**: diseño, seguridad y revisión. Opus implementa las tareas de seguridad, revisa las
  marcadas "lista para revisión", corrige o devuelve con `- Devuelta: …`, y **marca la casilla**
  solo al aprobar.
- Rutas: backend en `backend/src/saber_uli/`, pruebas en `backend/tests/`, frontend en
  `frontend/src/` y `frontend/tests/`.
- Toda prueba que use base de datos usa `postgres:18` real (Testcontainers); el proveedor OIDC se
  simula (respx en backend, `mock-oauth2-server` en e2e). Ninguna prueba llama a Entra ID real.
- El reloj se inyecta (`Clock`); ninguna prueba depende de la hora real.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Esqueleto del monorepo, herramientas y contenedores (plan → Project Structure).

- [x] T001 Crear el esqueleto del monorepo según plan.md: carpetas `backend/src/saber_uli/{shared,identity,notifications}/{domain,application,infrastructure,api}/` con `__init__.py`, `backend/tests/{unit,integration,contract,infra}/`, `backend/migrations/`, `frontend/`, `infra/{nginx,docker,postgres/init}/`, más `.gitignore`, `.gitattributes` (`* text=auto eol=lf`) y `.editorconfig` en la raíz → Qwen
  - Terminado: el árbol coincide con plan.md; `git status` no muestra archivos generados ni `.env`.
  - Estado: lista para revisión. Árbol creado según plan.md; se agregaron `.gitignore`,
    `.gitattributes`, `.editorconfig` y `.dockerignore` raíz (los contextos de build de Docker
    usan la raíz del repositorio).
  - Aprobada por Opus (2026-10-06): árbol completo frente a plan.md; `.env` ignorado; ningún
    archivo generado (`dist/`, `node_modules/`, `__pycache__/`) versionado.
- [x] T002 Crear `backend/pyproject.toml` y `backend/uv.lock` con Python 3.13; dependencias de ejecución: fastapi, uvicorn[standard], pydantic>=2, pydantic-settings, sqlalchemy[asyncio]>=2, asyncpg, alembic, authlib, httpx, itsdangerous, pyjwt, celery[redis], redis, structlog, limits, holidays, jinja2, opentelemetry-sdk (opcional); desarrollo: pytest, pytest-asyncio, pytest-cov, testcontainers[postgres,redis], respx, schemathesis, ruff, mypy, import-linter; configurar ruff, `mypy --strict`, pytest (`asyncio_mode=auto`) y cobertura con `fail_under = 80` sobre `saber_uli/*/domain` y `saber_uli/*/application`; script `saber-uli = "saber_uli.cli:app"` → Qwen
  - Terminado: `uv sync` funciona; `uv run pytest` corre (0 pruebas); `uv run ruff check .` y `uv run mypy --strict src` pasan.
  - Estado: lista para revisión. `pyproject.toml` (Python 3.13, ruff, mypy strict, pytest
    `asyncio_mode=auto`, cobertura `fail_under=80` acotada a `domain`/`application`) y `uv.lock`
    generados; `opentelemetry-sdk` queda como extra `otel`. Nota: se agregó una prueba de humo de
    empaquetado (`tests/unit/test_smoke.py`) para que `uv run pytest` salga en verde en lugar del
    código 5 de "sin pruebas"; no sustituye ninguna prueba funcional.
  - Aprobada por Opus (2026-10-06): `uv sync`, `pytest`, `ruff check`, `ruff format --check` y
    `mypy --strict src` en verde. La prueba de humo se acepta.
- [x] T003 [P] Definir los contratos de capas y contextos en `backend/.importlinter`: capas `api > application > domain` e `infrastructure > application > domain` en cada contexto; `domain` no importa fastapi, sqlalchemy, pydantic, celery ni redis; `identity` y `notifications` solo se importan entre sí a través de `<contexto>.application.public` → Opus
  - Estado: implementada por Opus en `backend/.importlinter`; se verifica con `lint-imports` cuando existan T001 y T002.
  - Nota: el orden de capas es `api > infrastructure > application > domain` (la API puede usar adaptadores solo para el cableado de FastAPI; la infraestructura nunca importa la API).
  - Terminado: `uv run lint-imports` pasa con el esqueleto y falla con un import prohibido de prueba (verificado y revertido).
  - Nota de Qwen (2026-10-06): con el esqueleto, `lint-imports` salía 1 porque las entradas
    `ignore_imports` de las fachadas aún no tienen coincidencias (alerta por defecto). Se agregó
    `unmatched_ignore_imports_alerting = warn` en los dos contratos afectados (la regla
    arquitectónica no cambia) y marcadores `identity/application/public.py` y
    `notifications/application/public.py` (los implementan T117 y T038). Verificado: 4 contratos
    KEPT con el esqueleto y BROKEN con un `import fastapi` de prueba en `shared/domain` (revertido).
    Queda a criterio de Opus al revisar T003.
  - Aprobada por Opus (2026-10-06): se acepta `unmatched_ignore_imports_alerting = warn`; cuando
    T038 y T117 hagan que las fachadas tengan importaciones reales, la tarea que lo logre debe
    quitar esa línea para que una excepción obsoleta vuelva a fallar. Nota de entorno: en Windows,
    con la salida redirigida a un archivo nulo, `lint-imports` sale 1 por un error de
    codificación cp1252 al imprimir acentos; usar `PYTHONIOENCODING=utf-8` (en CI, Linux, no
    ocurre).
- [x] T004 [P] Inicializar el frontend en `frontend/` con Vite + React + TypeScript (`strict: true`), dependencias: @tanstack/react-router, @tanstack/react-query, zustand, tailwindcss, shadcn/ui (componentes base), motion, react-hook-form, zod, @hookform/resolvers, dexie, i18next, react-i18next, vite-plugin-pwa; desarrollo: vitest, @testing-library/react, @testing-library/user-event, msw, @playwright/test, @axe-core/playwright, @lhci/cli, orval, eslint (typescript-eslint, jsx-a11y), prettier; scripts `dev`, `build`, `lint`, `typecheck`, `test`, `test:e2e`, `api:generate` en `frontend/package.json` → Qwen
  - Terminado: `npm ci`, `npm run lint`, `npm run typecheck`, `npm test` y `npm run build` pasan.
  - Estado: lista para revisión. Vite 8 + React 19 + TS estricto; Tailwind v4; base shadcn/ui
    (button, card, input, label + `cn`) en `src/shared/ui/`; eslint 9 (typescript-eslint,
    jsx-a11y) y prettier configurados; prueba de humo de la cadena de herramientas en
    `tests/unit/toolchain.test.tsx`. Notas: `eslint-plugin-jsx-a11y` exige eslint ^9 (se fijó esa
    versión); `App.tsx` es un marcador que T060/T061 sustituyen (su prueba fallará como exige
    TDD); vite-plugin-pwa queda instalado pero se configura en T068.
  - Aprobada por Opus (2026-10-06): `npm ci`, `lint`, `typecheck`, `test` y `build` en verde.
- [x] T005 [P] Configurar `frontend/orval.config.ts` para generar el cliente y los hooks de TanStack Query desde `specs/001-identidad-acceso/contracts/openapi.yaml` hacia `frontend/src/api/` usando el mutador `frontend/src/shared/api/http.ts` (stub que T047 completa) → Qwen
  - Terminado: `npm run api:generate` genera código que compila; `frontend/src/api/` tiene cabecera "generado, no editar".
  - Estado: implementada por Qwen (sin línea de estado ni commit; los cerró Opus). orval 8 en modo
    `tags` con cliente `react-query`, esquemas en `src/api/model/` y mutador
    `src/shared/api/http.ts` (stub con `fetch` y error RFC 9457). El mutador lo completa T063, no
    T047 (erratum de la descripción).
  - Aprobada por Opus (2026-10-06): la generación es determinista (dos ejecuciones dan el mismo
    hash del árbol), las URL llevan el prefijo `/api`, `src/api/` está excluido de eslint y
    prettier, y `typecheck`, `lint`, `test` y `build` pasan con el código generado.
- [ ] T006 [P] Crear `.pre-commit-config.yaml` con ruff, ruff-format, mypy (backend), eslint y prettier (frontend), detección de secretos (`detect-secrets`) y verificación de Conventional Commits (`commitizen`) → Qwen
  - Terminado: `pre-commit run --all-files` pasa; un mensaje de commit sin formato convencional es rechazado.
- [ ] T007 Prueba de infraestructura en `backend/tests/infra/test_containers.py` (sin dependencias nuevas: CLI de Docker por `subprocess`; se omite con `pytest.mark.skipif` si Docker no está disponible): `docker compose config` válido para `compose.yaml` + override y + prod; la imagen del backend corre con UID 10001; tras `docker compose up -d --wait` todos los servicios están `healthy` y `migrate` sale con código 0; `curl -I` al proxy muestra `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` y, para `sw.js`, `Service-Worker-Allowed: /`; `docker compose top` no muestra ningún proceso principal con UID 0; en `db` existen los roles `saber_migrator`, `saber_app` y `saber_bi` y las extensiones `citext` y `pg_stat_statements`; `actionlint` valida `.github/workflows/ci.yml` y el flujo contiene los trabajos `infra`, `backend-quality`, `backend-tests`, `contract`, `frontend-quality`, `e2e`, `lighthouse`, `build` y `security`. Si Docker no está disponible la prueba se omite, salvo con `REQUIRE_DOCKER=1`, en cuyo caso falla (constitución IV y X, research R-32 y R-33) → Qwen
  - Terminado: la prueba existe y falla porque aún no hay Dockerfiles, Compose, Nginx, scripts de inicio de Postgres ni flujo de CI.
- [ ] T008 [P] Crear `backend/Dockerfile` multi-etapa (builder con uv; runtime `python:3.13-slim`, usuario no root UID 10001, sin herramientas de compilación) con comandos para `api` (uvicorn, 4 workers), `worker` (celery worker), `beat` (celery beat con archivo de latido en `/tmp/beat-heartbeat`) y `migrate` (`saber-uli migrate`) → Qwen
  - Terminado: `docker build` funciona; `docker run --rm <img> id -u` devuelve 10001; la parte de imagen de T007 pasa.
- [ ] T009 [P] Crear `frontend/Dockerfile` multi-etapa (build con Node 24; final `nginxinc/nginx-unprivileged` que copia `dist/` y `infra/nginx/`) → Qwen
  - Terminado: la imagen sirve `index.html` en el puerto 8080 sin root; la imagen corre sin UID 0 según T007.
- [ ] T010 [P] Escribir la configuración de Nginx en `infra/nginx/default.conf` y `infra/nginx/security-headers.conf`: proxy de `/api/` a `api:8000`; `sw.js` y `manifest.webmanifest` con `Cache-Control: no-cache` y `Service-Worker-Allowed: /`; fallback SPA a `index.html`; cabeceras `Content-Security-Policy` (sin `unsafe-inline` en `script-src`, `connect-src 'self'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` restrictiva, `X-Frame-Options: DENY`; HSTS solo en `infra/nginx/tls.conf` para producción (research R-33) → Opus
  - Estado: implementada por Opus en `infra/nginx/{default.conf,locations.conf,security-headers.conf,tls.conf}`; falta verificarla en contenedor con T007.
  - Nota para T009: copiar `default.conf` a `/etc/nginx/conf.d/default.conf` y los demás archivos de `infra/nginx/` a `/etc/nginx/saber/` (no a `conf.d/`, porque Nginx incluye todo `conf.d/*.conf` en el contexto http).
  - Nota para T012: en `compose.prod.yaml`, montar `infra/nginx/tls.conf` sobre `/etc/nginx/conf.d/default.conf` y los certificados en `/etc/nginx/certs/{fullchain.pem,privkey.pem}`; puertos 80→8080 y 443→8443. `api` debe arrancar Uvicorn con `--proxy-headers --forwarded-allow-ips` limitado a la red de Compose, para que los límites por IP (T035) usen la IP real.
  - Nota para T068: registrar el service worker con `injectRegister: 'script'` (la CSP no admite scripts en línea).
  - Terminado: `nginx -t` pasa en el contenedor; la parte de cabeceras de T007 pasa; `/api/health` llega a la API.
- [ ] T011 [P] Crear `infra/postgres/init/01-roles.sql` y `02-extensions.sql`: roles `saber_migrator` (DDL), `saber_app` (DML), `saber_bi` (solo lectura de `analytics`, sin objetos aún) con contraseñas desde variables de entorno; extensiones `citext` y `pg_stat_statements` (research R-07) → Opus
  - Estado: implementada por Opus en `infra/postgres/init/{01-roles.sql,02-extensions.sql}`; falta verificarla en contenedor con T007 y T029.
  - Nota para T012 y T013: el servicio `db` necesita `SABER_MIGRATOR_PASSWORD`, `SABER_APP_PASSWORD` y `SABER_BI_PASSWORD` (mínimo 16 caracteres; sin ellas el contenedor no arranca) y el comando `postgres -c shared_preload_libraries=pg_stat_statements`. T024 debe pasar las mismas variables al contenedor de Testcontainers.
  - Terminado: la parte de roles y extensiones de T007 pasa al iniciar `db` desde cero; el superusuario no se usa en ningún otro servicio.
- [ ] T012 Crear `compose.yaml` (servicios `proxy`, `api`, `worker`, `beat`, `migrate`, `db` con volumen en `/var/lib/postgresql`, `redis`), `compose.override.yaml` (recarga en caliente, `mailpit`, puertos locales) y `compose.prod.yaml` (TLS, `tls.conf`, sin mailpit); perfil `e2e` con `oidc` (`ghcr.io/navikt/mock-oauth2-server`, configuración en `infra/docker/mock-oauth2.json` con un emisor del inquilino válido y otro externo) y `mailpit`; `user:` explícito sin privilegios en `mailpit` y `oidc`; health checks y `depends_on` según la tabla de servicios de plan.md → Qwen
  - Terminado: T007 pasa completa (Compose válido, servicios `healthy`, `migrate` con código 0 y ningún proceso principal con UID 0).
- [ ] T013 [P] Crear `.env.example` documentado: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_AUTHORITY`, `PUBLIC_BASE_URL`, `INSTITUTIONAL_EMAIL_DOMAINS`, `JWT_SIGNING_KEY`, `JWT_KEY_ID`, `SESSION_COOKIE_SECRET`, `DATABASE_URL` (por rol), `REDIS_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `OTEL_ENABLED`, `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` (reservadas para la spec 009), contraseñas de roles de base de datos → Qwen
  - Terminado: cada variable tiene comentario en español; ningún valor real; `.env` está en `.gitignore`.
- [ ] T014 [P] Crear `.github/workflows/ci.yml` con los trabajos `infra` (`pytest backend/tests/infra`), `backend-quality` (ruff, mypy, lint-imports), `backend-tests` (pytest con cobertura y `fail_under`), `contract` (Schemathesis), `frontend-quality` (lint, typecheck, vitest, verificación de que `npm run api:generate` no deja cambios), `e2e` (compose perfil `e2e` + Playwright), `lighthouse`, `build` (imágenes) y `security` (Trivy sobre imágenes y sistema de archivos, falla con severidad CRITICAL/HIGH); y `.github/dependabot.yml` para pip, npm, docker y actions → Qwen
  - Terminado: la parte de CI de T007 pasa; el trabajo `infra` ejecuta `pytest backend/tests/infra` con `REQUIRE_DOCKER=1`; los trabajos fallan si fallan sus pasos.
- [ ] T015 [P] Redactar el borrador de política `backend/seeds/politica_tratamiento_datos_v1.md` (responsable, finalidades, datos recogidos según FR-004 y FR-019/020, derechos de consulta, rectificación, revocación y supresión, plazos de conservación de FR-034a/b, canales de atención), marcado "BORRADOR — pendiente de aprobación de la oficina jurídica" → Opus
  - Estado: borrador redactado por Opus en `backend/seeds/politica_tratamiento_datos_v1.md`; los datos del responsable y los canales quedan como `[PENDIENTE]` hasta que la oficina jurídica los apruebe (riesgo externo de plan.md).
  - Terminado: cumple FR-016 (finalidad, datos, derechos y canales) y supera 200 caracteres (restricción del contrato).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Kernel compartido, esquema de datos, sesión propia, autorización, guardia de
consentimiento, correo y base del frontend. Ninguna historia empieza antes de terminar esta fase.

### Kernel compartido (backend)

- [ ] T016 [P] Prueba: configuración por entorno en `backend/tests/unit/shared/test_config.py` (carga de variables de T013, error claro si falta un secreto obligatorio, `INSTITUTIONAL_EMAIL_DOMAINS` como lista, secretos excluidos de `repr`) → Qwen
  - Terminado: la prueba falla porque no existe `config.py`.
- [ ] T017 Implementar `backend/src/saber_uli/config.py` con pydantic-settings para que pase T016 → Qwen
  - Terminado: T016 en verde.
- [ ] T018 [P] Prueba: procesador de logs sin datos personales en `backend/tests/unit/shared/test_logging.py` (elimina o enmascara las claves `email`, `name`, `correo`, `nombre`, `token`, `authorization`, `cookie`, `code`, `display_name`; enmascara cualquier valor con forma de correo; salida JSON; research R-23) → Opus
  - Terminado: la prueba falla.
- [ ] T019 Implementar `backend/src/saber_uli/shared/infrastructure/logging.py` (structlog JSON + procesador de T018) → Opus
  - Terminado: T018 en verde.
- [ ] T020 [P] Prueba: Problem Details y paginación en `backend/tests/unit/shared/test_problems.py` (respuesta `application/problem+json`, `type` = `urn:saber-uli:problem:<slug>`, `errors` por campo en 422, `page`≥1, `page_size` 1–100 por defecto 25, `total`) → Qwen
  - Terminado: la prueba falla.
- [ ] T021 Implementar `backend/src/saber_uli/shared/api/problems.py` (excepciones de dominio → Problem, manejadores de FastAPI, incluido 422 de validación) y `backend/src/saber_uli/shared/api/pagination.py` → Qwen
  - Terminado: T020 en verde.
- [ ] T022 [P] Prueba: bloques de dominio en `backend/tests/unit/shared/test_domain_base.py` (`DomainEvent` con `event_id` uuid y `occurred_at`; `Clock` del sistema y `FixedClock` para pruebas; errores de dominio con slug) → Qwen
  - Terminado: la prueba falla.
- [ ] T023 Implementar `backend/src/saber_uli/shared/domain/{events.py,clock.py,errors.py}` → Qwen
  - Terminado: T022 en verde; `lint-imports` confirma que `shared.domain` no importa infraestructura.
- [ ] T024 [P] Crear fixtures de pruebas en `backend/tests/conftest.py` y `backend/tests/integration/conftest.py`: contenedores `postgres:18` (con los scripts de `infra/postgres/init/`) y `redis:8`, aplicación de migraciones, sesión por prueba con rollback, `FixedClock`, cliente `httpx.AsyncClient` sobre la app ASGI, fábrica de usuarios por rol y emisor de tokens de prueba → Qwen
  - Terminado: una prueba de humo de integración arranca los contenedores y hace `SELECT 1` con el rol `saber_app`.
- [ ] T025 [P] Prueba: unidad de trabajo en `backend/tests/integration/shared/test_unit_of_work.py` (commit persiste; excepción hace rollback; eventos del bus en proceso se despachan solo tras el commit) → Qwen
  - Terminado: la prueba falla.
- [ ] T026 Implementar `backend/src/saber_uli/shared/infrastructure/db.py` (engine asyncpg, sesiones), `backend/src/saber_uli/shared/application/unit_of_work.py`, `backend/src/saber_uli/shared/application/event_bus.py` y `backend/migrations/env.py` (Alembic asíncrono, varios esquemas, `alembic_version` en `shared`) → Qwen
  - Terminado: T025 en verde; `saber-uli migrate` aplica cero migraciones sin error.

### Esquema de datos

- [ ] T027 [P] Prueba: restricciones del esquema en `backend/tests/integration/identity/test_schema_constraints.py`, citando data-model.md: `users.kind IN ('institutional','guest')`; `users.status IN ('active','disabled','deletion_pending','deleted')`; `UNIQUE (entra_tenant_id, entra_object_id)`; una lápida (`status='deleted'`) exige `email`, `display_name` y `entra_object_id` en `NULL`; índice único parcial de correo de invitado vigente; `profiles.semester BETWEEN 1 AND 12`; `daily_goal IN ('casual','regular','intense')`; `role IN ('student','guest','teacher','program_director','admin')`; `invitations.status IN ('sent','accepted','expired','revoked')` y una sola invitación `sent|accepted` por correo; `access_links.purpose IN ('invitation','sign_in')` y `token_hash` único; `consents.decision IN ('accepted','rejected','revoked')`; `deletion_requests.origin` y `status` según data-model §2.12 con una sola solicitud abierta por usuario; claves por defecto `uuidv7()` → Qwen
  - Terminado: la prueba falla porque las tablas no existen.
- [ ] T028 Implementar las migraciones `backend/migrations/versions/0001_shared_outbox.py` (esquema `shared`, `outbox_events` con índice parcial `(available_at) WHERE processed_at IS NULL`) y `backend/migrations/versions/0002_identity_schema.py` (todas las tablas de data-model.md §2 con sus `CHECK`, FK, índices y extensión `citext`) → Qwen
  - Terminado: T027 en verde; `alembic downgrade base` y `upgrade head` funcionan.
- [ ] T029 [P] Prueba: permisos de base de datos en `backend/tests/integration/identity/test_db_grants.py`: con el rol `saber_app`, `UPDATE` y `DELETE` sobre `identity.audit_events` y `identity.consents` fallan, `UPDATE` sobre `identity.policy_versions` falla, `INSERT`/`SELECT` funcionan; `saber_app` no puede ejecutar DDL; `saber_bi` no lee el esquema `identity` (FR-035, research R-07) → Opus
  - Terminado: la prueba falla.
- [ ] T030 Implementar `backend/migrations/versions/0003_identity_grants.py` (grants por rol, `ALTER DEFAULT PRIVILEGES`, revocaciones de `UPDATE`/`DELETE` en tablas de solo inserción) → Opus
  - Terminado: T029 en verde.

### Outbox, worker y límites

- [ ] T031 [P] Prueba: outbox en `backend/tests/integration/shared/test_outbox.py` (evento escrito en la misma transacción; rollback no deja evento; despacho con `FOR UPDATE SKIP LOCKED` sin doble entrega con dos despachadores concurrentes; manejador idempotente por `event_id`; reintento con espera y `last_error` sin datos personales; purga a los 7 días de procesado; payload rechazado si contiene claves `email`, `name` o `token`) → Qwen
  - Terminado: la prueba falla.
- [ ] T032 Implementar `backend/src/saber_uli/shared/infrastructure/outbox.py` (escritor, despachador, registro de manejadores, purga) para que pase T031 → Qwen
  - Terminado: T031 en verde.
- [ ] T033 [P] Prueba: programación de Celery en `backend/tests/unit/test_worker_schedule.py` (zona `America/Bogota`; `dispatch_outbox` cada 5 s; `expire_invitations` cada hora; `process_retention` diaria 02:00; `process_deletion_requests` cada 15 min; `purge_expired_auth_artifacts` diaria; research R-09) → Qwen
  - Terminado: la prueba falla.
- [ ] T034 Implementar `backend/src/saber_uli/worker.py` (app Celery, Beat, tarea `dispatch_outbox`; las demás tareas como registros que cada historia completa) → Qwen
  - Terminado: T033 en verde; el servicio `worker` responde a `celery inspect ping`.
- [ ] T035 [P] Prueba: limitación de peticiones en `backend/tests/integration/shared/test_rate_limit.py` (ventanas de research R-31: 5/h por hash de correo y 20/h por IP en solicitud de enlace; 10/min por IP en consumo de enlace; 30/min por IP en ingreso Microsoft y renovación; 300/min por usuario en el resto; respuesta 429 `rate-limited` con `Retry-After`; la clave por correo usa hash, nunca el correo) → Opus
  - Terminado: la prueba falla.
- [ ] T036 Implementar `backend/src/saber_uli/shared/infrastructure/rate_limit.py` y la dependencia FastAPI en `backend/src/saber_uli/shared/api/rate_limit.py` con `limits` + Redis → Opus
  - Terminado: T035 en verde.

### Correo (contexto notifications)

- [ ] T037 [P] Prueba: correo en `backend/tests/unit/notifications/test_templates.py` (plantillas HTML y texto en es-CO, autoescape activo, enlaces absolutos con `PUBLIC_BASE_URL`) y `backend/tests/integration/notifications/test_smtp_sender.py` (envío real a un contenedor Mailpit, verificado por su API) → Qwen
  - Terminado: las pruebas fallan.
- [ ] T038 Implementar `backend/src/saber_uli/notifications/application/public.py` (fachada `send_email(template, to, context)`), `backend/src/saber_uli/notifications/application/ports.py` (`EmailSender`), `backend/src/saber_uli/notifications/infrastructure/smtp.py` (smtplib) y `backend/src/saber_uli/notifications/infrastructure/templates/base.{html,txt}.j2` → Qwen
  - Terminado: T037 en verde; los logs del envío no contienen el destinatario.

### Identidad: usuarios, permisos, sesiones y guardias

- [ ] T039 [P] Prueba: matriz de permisos en `backend/tests/unit/identity/test_permissions.py` (permisos de cada rol según research R-22 y el enum `Permission` del contrato; unión de permisos para varios roles (FR-023); `guest` sin permisos de gestión; `teacher` con `invitations:manage_own` y `groups:read_own_students`; `program_director` con `programs:read_aggregated` y sin permisos que expongan datos personales (FR-026); `admin` con todos) → Opus
  - Terminado: la prueba falla.
- [ ] T040 Implementar `backend/src/saber_uli/identity/domain/roles.py` y `backend/src/saber_uli/identity/domain/permissions.py` → Opus
  - Terminado: T039 en verde.
- [ ] T041 [P] Prueba: agregado `User` en `backend/tests/unit/identity/test_user.py` (creación institucional con `student`; transiciones `active↔disabled`, `→deletion_pending→deleted` y `deleted` final; cada transición que revoca sesiones incrementa `auth_epoch`; registrar ingreso actualiza `last_login_at` y limpia `retention_notice_sent_at`; `to_tombstone()` deja nombre, correo y `oid` en `None`) → Qwen
  - Terminado: la prueba falla.
- [ ] T042 Implementar `backend/src/saber_uli/identity/domain/user.py` → Qwen
  - Terminado: T041 en verde.
- [ ] T043 [P] Prueba: repositorios en `backend/tests/integration/identity/test_user_repository.py` (guardar y leer `User` con roles; buscar por `(tid, oid)`; búsqueda de invitado vigente por correo sin distinguir mayúsculas; bloqueo de administradores activos con `FOR UPDATE`) → Qwen
  - Terminado: la prueba falla.
- [ ] T044 Implementar `backend/src/saber_uli/identity/infrastructure/orm.py` (mapeos SQLAlchemy de data-model.md) y `backend/src/saber_uli/identity/infrastructure/repositories/users.py` → Qwen
  - Terminado: T043 en verde.
- [ ] T045 [P] Prueba: política de sesión y tokens en `backend/tests/unit/identity/test_session_policy.py` (JWT HS256 de 600 s con `kid` y claims `sub`, `sid`, `roles`, `epoch`, `priv`, `iat`, `exp`; token de renovación de 256 bits guardado solo como SHA-256; rotación en cada uso; reutilizar un token rotado revoca la sesión; inactividad 7 días y absoluto 30 días; `priv=true` solo con rol privilegiado, `auth_time` < 12 h y actividad privilegiada < 30 min; una sesión recién creada o reautenticada inicializa `last_privileged_activity_at = auth_time`, así que un administrador recién autenticado obtiene `priv=true`; con 31 min sin actividad privilegiada obtiene `priv=false`; research R-14 y R-15) → Opus
  - Terminado: la prueba falla.
- [ ] T046 Implementar `backend/src/saber_uli/identity/domain/session.py`, `backend/src/saber_uli/identity/infrastructure/tokens.py` y `backend/src/saber_uli/identity/infrastructure/repositories/sessions.py` → Opus
  - Terminado: T045 en verde.
- [ ] T047 [P] Prueba: dependencia de autenticación en `backend/tests/integration/identity/test_auth_dependency.py` (sin token → 401 `unauthenticated`; `epoch` distinto → 401 con causa `account-disabled`, `guest-access-expired`, `guest-access-revoked` o `session-revoked`; ruta `x-requires-privileged-session` sin `priv` → 401 `reauthentication-required`; `auth_epoch` leído de Redis con respaldo en base de datos si Redis falla; la actividad privilegiada actualiza `last_privileged_activity_at`; research R-16) → Opus
  - Terminado: la prueba falla.
- [ ] T048 Implementar `backend/src/saber_uli/shared/api/auth.py` (dependencias `current_user` y `require_privileged`), `backend/src/saber_uli/identity/application/access_guard.py` y `backend/src/saber_uli/identity/infrastructure/epoch_cache.py` → Opus
  - Terminado: T047 en verde.
- [ ] T049 [P] Prueba: renovación y cierre de sesión en `backend/tests/integration/identity/test_refresh_logout.py` (`POST /api/auth/refresh` exige `X-Requested-With: saber-uli`; cookie `su_refresh` con `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/auth`; rota la cookie; reutilización → 401 `session-revoked` y familia revocada; cuenta desactivada → 401 `account-disabled`; inactividad > 7 días → 401 `session-expired`; `POST /api/auth/logout` → 204 y cookie borrada; escenario 1.4) → Opus
  - Terminado: la prueba falla.
- [ ] T050 Implementar `backend/src/saber_uli/identity/application/sessions.py` y `backend/src/saber_uli/identity/api/auth_router.py` (refresh y logout) → Opus
  - Terminado: T049 en verde.
- [ ] T051 [P] Prueba: estado de autorización y guardia de consentimiento en `backend/tests/unit/identity/test_consent_status.py` (vigente solo si el último registro es `accepted` y su versión es la vigente; sin registros, `rejected`, `revoked` o versión anterior → `consent_required`) y `backend/tests/integration/identity/test_consent_guard.py` (ruta sin `x-consent-exempt` → 403 `consent-required`; rutas exentas responden; FR-014) → Qwen
  - Terminado: las pruebas fallan.
- [ ] T052 Implementar `backend/src/saber_uli/identity/domain/consent.py` (estado vigente), `backend/src/saber_uli/identity/application/queries/consent_status.py` y `backend/src/saber_uli/shared/api/consent_guard.py` (lista de rutas exentas tomada del contrato) → Qwen
  - Terminado: T051 en verde.
- [ ] T053 [P] Prueba: auditoría en `backend/tests/integration/identity/test_audit_writer.py` (el evento se escribe en la misma transacción que la acción; `action` del catálogo de data-model §5; rechaza `details` con claves `email`, `name`, `display_name` o valores con forma de correo; `actor_id` `NULL` = sistema) → Qwen
  - Terminado: la prueba falla.
- [ ] T054 Implementar `backend/src/saber_uli/identity/application/audit.py` y `backend/src/saber_uli/identity/infrastructure/repositories/audit.py` → Qwen
  - Terminado: T053 en verde.
- [ ] T055 [P] Prueba: parámetros en `backend/tests/unit/identity/test_settings.py` (valores por defecto `teacher_max_access_days`=180, `default_guest_access_days`=90, `invitation_link_ttl_days`=7, `sign_in_link_ttl_minutes`=15; rangos del contrato: 1–730, 1–730, 1–30, 5–60) → Qwen
  - Terminado: la prueba falla.
- [ ] T056 Implementar `backend/src/saber_uli/identity/domain/settings.py` y `backend/src/saber_uli/identity/infrastructure/repositories/settings.py` (con semilla de valores por defecto en la migración `backend/migrations/versions/0004_identity_settings_seed.py`) → Qwen
  - Terminado: T055 en verde.
- [ ] T057 [P] Prueba: arranque de la API en `backend/tests/integration/test_health.py` (`GET /api/health` → `{"status":"ok"}`; `GET /api/ready` → 503 si la base de datos o Redis no responden; logs JSON en cada petición sin datos personales) → Qwen
  - Terminado: la prueba falla.
- [ ] T058 Implementar `backend/src/saber_uli/main.py` (app FastAPI, routers, manejadores de problemas, logging, `SessionMiddleware` acotada a `/api/auth/microsoft`) y `backend/src/saber_uli/shared/api/health.py` → Qwen
  - Terminado: T057 en verde; `docker compose up` deja `api` en `healthy`.
- [ ] T059 Crear el arnés de contrato `backend/tests/contract/test_openapi_contract.py` con Schemathesis sobre la app ASGI, autenticado con tokens de prueba por rol, y la lista `backend/tests/contract/implemented_operations.py` (cada historia agrega sus `operationId`) → Qwen
  - Terminado: corre en verde con las operaciones de la fase 2 (`getHealth`, `getReadiness`, `refreshSession`, `logout`).

### Base del frontend

- [ ] T060 [P] Prueba: shell de la app en `frontend/src/app/App.test.tsx` (renderiza en es-CO, idioma `lang="es-CO"`, indicador de estado de conexión visible, navegación accesible por teclado) → Qwen
  - Terminado: la prueba falla.
- [ ] T061 Implementar `frontend/src/app/{main.tsx,router.tsx,providers.tsx,AppShell.tsx}`, `frontend/src/shared/i18n/{index.ts,es-CO.json}` y la base de Tailwind/shadcn en `frontend/src/shared/ui/` → Qwen
  - Terminado: T060 en verde.
- [ ] T062 [P] Prueba: sesión en memoria y cliente HTTP en `frontend/src/features/auth/session.test.ts` con MSW (el token de acceso vive solo en memoria y nunca en `localStorage`/`sessionStorage`/IndexedDB; cabecera `Authorization`; ante 401 intenta una sola renovación con `X-Requested-With: saber-uli` y reintenta; cada `type` de problema se traduce a un mensaje en español) → Opus
  - Terminado: la prueba falla.
- [ ] T063 Implementar `frontend/src/shared/api/http.ts` (mutador de orval), `frontend/src/features/auth/session-store.ts` (Zustand sin persistencia) y `frontend/src/shared/api/problem-messages.ts` → Opus
  - Terminado: T062 en verde.
- [ ] T064 [P] Prueba: acceso sin conexión en `frontend/src/features/auth/offline-access.test.ts` (guarda la instantánea de `/api/v1/me` y `lastValidatedAt` en Dexie; sin red permite usar la app si `ahora − lastValidatedAt ≤ 7 días`; después bloquea con mensaje; al reconectar llama primero a `/api/auth/refresh` y luego a `/api/v1/me` antes de permitir sincronizar; FR-038, FR-039) → Qwen
  - Terminado: la prueba falla.
- [ ] T065 Implementar `frontend/src/shared/db/dexie.ts` y `frontend/src/features/auth/offline-access.ts` (incluye el hook `useCanSync` que la spec 003 usará) → Qwen
  - Terminado: T064 en verde.
- [ ] T066 [P] Prueba: guardias de navegación en `frontend/src/app/guards.test.tsx` (sin sesión → `/ingresar`; `consent_required` → `/bienvenida/datos`; `profile_required` → `/bienvenida/perfil`; rutas de administración y docente según `permissions`; retomar el paso pendiente del primer ingreso, FR-022) → Qwen
  - Terminado: la prueba falla.
- [ ] T067 Implementar `frontend/src/app/guards.ts` y su conexión en `frontend/src/app/router.tsx` → Qwen
  - Terminado: T066 en verde.
- [ ] T068 [P] Configurar la PWA en `frontend/vite.config.ts` (vite-plugin-pwa: manifest con nombre "Saber Uli", `lang: es-CO`, íconos 192/512 y maskable en `frontend/public/icons/`, `display: standalone`, precache del shell) y la guía de instalación para iPhone en `frontend/src/shared/ui/InstallHint.tsx` con su prueba `frontend/src/shared/ui/InstallHint.test.tsx` → Qwen
  - Terminado: `npm run build` genera `sw.js` y `manifest.webmanifest`; la prueba del componente pasa.
- [ ] T069 [P] Configurar Playwright en `frontend/playwright.config.ts` (viewport móvil Pixel 7 e iPhone 14, `locale: es-CO`) y los fixtures `frontend/tests/e2e/fixtures/{auth.ts,mailpit.ts,axe.ts,api.ts}` (ingreso con el proveedor de prueba eligiendo usuario del inquilino o externo; lectura de correos de Mailpit; chequeo axe nivel AA; llamadas API como administrador) → Qwen
  - Terminado: una prueba de humo abre `/` contra el stack con perfil `e2e`.
- [ ] T070 Revisión de seguridad de la fase 2 (T010, T011, T029–T030, T035–T036, T045–T050, T062–T063) en `specs/001-identidad-acceso/tasks.md`: ASVS 4.0.3 V2, V3, V4 y V7 aplicables; secretos solo por entorno; ningún dato personal en logs ni outbox → Opus
  - Terminado: hallazgos corregidos o registrados como tareas nuevas; casillas de la fase 2 marcadas.

**Checkpoint**: base lista; las historias pueden empezar (en paralelo si hay capacidad).

---

## Phase 3: User Story 1 - Ingreso con la cuenta institucional (Priority: P1) 🎯 MVP

**Goal**: un miembro de Unilibre entra con Microsoft 365, se crea su cuenta con rol Estudiante y
llega al paso de autorización; cualquier otra cuenta Microsoft es rechazada con un mensaje claro.

**Independent Test**: con el proveedor de prueba, ingresar con un usuario del inquilino (cuenta
creada, redirige a `/bienvenida/datos`) y con uno externo (rechazo, sin cuenta); cerrar sesión.

### Tests for User Story 1 ⚠️

- [ ] T071 [P] [US1] Prueba: caso de uso en `backend/tests/unit/identity/test_authenticate_institutional_user.py` (primer ingreso crea usuario `institutional` con rol `student`, nombre y correo de los claims (FR-003); ingreso posterior reutiliza la cuenta por `(tid, oid)` y actualiza nombre y correo (FR-005, escenario 1.3); `tid` distinto → error `tenant_not_allowed` sin crear cuenta (FR-002); cuenta `disabled` → `account-disabled`; registra `last_login_at`; audita `user.created` solo en el primer ingreso) → Qwen
  - Terminado: la prueba falla.
- [ ] T072 [P] [US1] Prueba: adaptador Entra ID en `backend/tests/integration/identity/test_entra_adapter.py` con respx y JWK generadas (descubrimiento por `.well-known`; PKCE S256; `state` y `nonce` en cookie firmada de 10 min; rechaza firma inválida, `aud` distinto, `nonce` distinto, `iss` de otro inquilino y `tid` distinto; usa la autoridad del inquilino, nunca `common`; toma solo `oid`, `tid`, `name`, `email` o `preferred_username`; research R-10 a R-13) → Opus
  - Terminado: la prueba falla.
- [ ] T073 [P] [US1] Prueba: flujo HTTP en `backend/tests/integration/identity/test_microsoft_login_flow.py` (`GET /api/auth/microsoft/login` → 302 a la autoridad del inquilino; `return_to` solo rutas relativas; callback válido → 302 a `/bienvenida/datos` y cookie `su_refresh`; inquilino externo → 302 a `/ingresar?error=tenant_not_allowed` sin crear usuario y log `auth.login_rejected` sin correo (FR-036); proveedor caído → `/ingresar?error=idp_unavailable`; rate limit 30/min por IP) → Opus
  - Terminado: la prueba falla.
- [ ] T074 [P] [US1] Prueba: `GET /api/v1/me` en `backend/tests/integration/identity/test_me.py` (campos del esquema `Me`; `permissions` según roles; `onboarding.consent_required` y `profile_required`; `access.offline_grace_until` = `validated_at` + 7 días; responde sin autorización de datos por ser exenta) → Qwen
  - Terminado: la prueba falla.
- [ ] T075 [P] [US1] Prueba de componente `frontend/src/features/auth/LoginPage.test.tsx` (botón "Ingresar con mi cuenta Unilibre"; mensaje para `tenant_not_allowed` con la alternativa de pedir invitación (SC-008); mensaje para `idp_unavailable`; enlace a ingreso de invitados) → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 1

- [ ] T076 [US1] Implementar `backend/src/saber_uli/identity/application/authenticate_institutional_user.py` para que pase T071 → Qwen
  - Terminado: T071 en verde.
- [ ] T077 [US1] Implementar `backend/src/saber_uli/identity/infrastructure/entra_id.py` (cliente Authlib) para que pase T072 → Opus
  - Terminado: T072 en verde.
- [ ] T078 [US1] Implementar `backend/src/saber_uli/identity/api/microsoft_router.py` (login y callback) para que pase T073 → Opus
  - Terminado: T073 en verde.
- [ ] T079 [US1] Implementar `backend/src/saber_uli/identity/application/queries/get_me.py` y `backend/src/saber_uli/identity/api/me_router.py` para que pase T074; agregar `startMicrosoftLogin`, `completeMicrosoftLogin` y `getMe` a `backend/tests/contract/implemented_operations.py` → Qwen
  - Terminado: T074 y la prueba de contrato en verde.
- [ ] T080 [US1] Implementar `frontend/src/features/auth/LoginPage.tsx` y `frontend/src/features/auth/bootstrap.ts` (tras volver de Microsoft: renovar, consultar `/me`, guardar instantánea, redirigir según guardias; botón de cerrar sesión en `AppShell`) → Qwen
  - Terminado: T075 en verde.
- [ ] T081 [US1] Prueba e2e `frontend/tests/e2e/us1-institutional-login.spec.ts` (usuario del inquilino llega a `/bienvenida/datos`; usuario externo ve el rechazo y no se crea cuenta; cerrar sesión exige ingresar de nuevo; axe sin infracciones AA en `/ingresar`) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T082 [US1] Revisión de US1 (T071–T081) en `specs/001-identidad-acceso/tasks.md`: validación OIDC, ausencia de datos personales en logs, mensajes de error y cumplimiento de FR-001 a FR-005 y FR-036 → Opus
  - Terminado: tareas aprobadas y marcadas; quickstart V2 verificado.

**Checkpoint**: US1 funciona y se demuestra sola.

---

## Phase 4: User Story 2 - Autorización de tratamiento de datos (Priority: P1)

**Goal**: aceptar o rechazar de forma explícita la política, consultarla y revocarla; sin
autorización vigente no se usa la plataforma; una versión nueva exige aceptarla de nuevo.

**Independent Test**: usuario nuevo rechaza (sin acceso), acepta (acceso), consulta y revoca
(acceso suspendido); el administrador publica la versión 1.1 y se exige aceptarla.

### Tests for User Story 2 ⚠️

- [ ] T083 [P] [US2] Prueba: semilla de la política en `backend/tests/integration/identity/test_policy_seed.py` (tras migrar existe la versión `1.0` vigente con el texto de `backend/seeds/politica_tratamiento_datos_v1.md`; volver a migrar no la duplica) → Qwen
  - Terminado: la prueba falla.
- [ ] T084 [P] [US2] Prueba: reglas de autorización en `backend/tests/unit/identity/test_consent.py` (decisión solo `accepted` o `rejected` sobre la versión vigente; revocar solo si hay autorización vigente (`no-active-consent`); decisión sobre versión no vigente → `policy-version-not-current`; publicar versión exige `version` con patrón `^[0-9]+\.[0-9]+$`, `body_markdown` de 200 a 100 000 caracteres y versión única) → Qwen
  - Terminado: la prueba falla.
- [ ] T085 [P] [US2] Prueba: API en `backend/tests/integration/identity/test_consent_api.py` (`GET/POST /api/v1/me/consents` registra usuario, fecha, versión, decisión y canal `web_pwa` (FR-015); `POST /api/v1/me/consents/revocation` incrementa `auth_epoch` y la siguiente petición responde 401 (escenario 2.5); `GET /api/v1/privacy-policy/current` y `/versions/{id}` sin autenticación; `POST /api/v1/admin/privacy-policy/versions` exige `policy:publish` y sesión privilegiada y audita `policy.published`; tras publicar, `/me` devuelve `consent_required=true` para todos (FR-017); auditoría `consent.accepted|rejected|revoked`) → Qwen
  - Terminado: la prueba falla.
- [ ] T086 [P] [US2] Pruebas de componente `frontend/src/features/onboarding/ConsentPage.test.tsx` (muestra finalidad, datos, derechos y canales; opciones "Acepto" y "No acepto" sin preselección; "No acepto" muestra la explicación con las opciones de aceptar luego o solicitar supresión) y `frontend/src/features/account/ConsentSettingsPage.test.tsx` (versión aceptada, fecha, ver texto, revocar con confirmación) → Qwen
  - Terminado: las pruebas fallan.

### Implementation for User Story 2

- [ ] T087 [US2] Registrar en `specs/001-identidad-acceso/research.md` la dependencia `react-markdown` (sin `rehype-raw`, HTML deshabilitado) para mostrar la política de forma segura, con justificación y alternativas → Opus
  - Terminado: entrada nueva en research.md; ningún otro artefacto de diseño cambia.
- [ ] T088 [US2] Implementar la migración `backend/migrations/versions/0005_seed_policy_v1.py` (carga idempotente de la versión 1.0) para que pase T083 → Qwen
  - Terminado: T083 en verde.
- [ ] T089 [US2] Implementar `backend/src/saber_uli/identity/domain/policy.py` y completar `backend/src/saber_uli/identity/domain/consent.py` para que pase T084 → Qwen
  - Terminado: T084 en verde.
- [ ] T090 [US2] Implementar `backend/src/saber_uli/identity/application/consent.py` (decidir, revocar con incremento de `auth_epoch`, publicar), `backend/src/saber_uli/identity/api/consent_router.py` y `backend/src/saber_uli/identity/api/policy_router.py` para que pase T085; agregar las 6 operaciones a `implemented_operations.py` → Qwen
  - Terminado: T085 y la prueba de contrato en verde.
- [ ] T091 [P] [US2] Implementar `frontend/src/features/onboarding/ConsentPage.tsx` y `frontend/src/features/account/ConsentSettingsPage.tsx` (Markdown con `react-markdown`) para que pase T086 → Qwen
  - Terminado: T086 en verde.
- [ ] T092 [P] [US2] Implementar `frontend/src/features/admin/PolicyPage.tsx` con su prueba `frontend/src/features/admin/PolicyPage.test.tsx` (publicar versión con vista previa; validación de versión y longitud) → Qwen
  - Terminado: prueba en verde.
- [ ] T093 [US2] Prueba e2e `frontend/tests/e2e/us2-consent.spec.ts` (V3 y V4 de quickstart: rechazar bloquea todo salvo política, cierre de sesión y supresión; aceptar da acceso; revocar cierra la sesión en la siguiente acción; nueva versión exige aceptación) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T094 [US2] Revisión de US2 (T083–T093) en `specs/001-identidad-acceso/tasks.md`: Ley 1581 (autorización expresa, finalidad, versiones), FR-014 a FR-018 y SC-002 → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: US1 + US2 funcionan; ningún usuario usa la plataforma sin autorización vigente.

---

## Phase 5: User Story 3 - Completar el perfil en el primer ingreso (Priority: P1)

**Goal**: el institucional completa solo programa, semestre, fecha de presentación y meta
diaria; el invitado, solo nombre, meta y fecha opcional; ambos pueden editarlo después.

**Independent Test**: tras autorizar, completar el perfil y llegar a `/inicio` en menos de
1 minuto desde el inicio del ingreso; editarlo desde `/mi-cuenta`.

### Tests for User Story 3 ⚠️

- [ ] T095 [P] [US3] Prueba: perfil en `backend/tests/unit/identity/test_profile.py` (institucional completo exige `program_id`, `semester` entre 1 y 12, `expected_exam_date` y `daily_goal` en `casual|regular|intense`; invitado completo exige `guest_display_name` de 2 a 120 caracteres y `daily_goal`, con `expected_exam_date` opcional, y rechaza `program_id` y `semester`; programa inactivo rechazado) → Qwen
  - Terminado: la prueba falla.
- [ ] T096 [P] [US3] Prueba: API en `backend/tests/integration/identity/test_profile_api.py` (`GET /api/v1/programs` solo activos; `GET/PUT /api/v1/me/profile`; completar fija `onboarding_completed_at` y `/me` devuelve `profile_required=false`; nombre y correo institucionales no son editables (FR-021); 403 `consent-required` sin autorización) → Qwen
  - Terminado: la prueba falla.
- [ ] T097 [P] [US3] Prueba de componente `frontend/src/features/onboarding/ProfilePage.test.tsx` (variante institucional con nombre y correo de solo lectura y cuatro campos; variante invitado con nombre, meta y fecha opcional; errores accesibles por campo) → Qwen
  - Terminado: la prueba falla.
- [ ] T098 [P] [US3] Prueba: comando `saber-uli identity import-programs --csv <archivo>` en `backend/tests/integration/identity/test_cli_import_programs.py` (CSV UTF-8 con encabezado `codigo,nombre,seccional`; `code` con patrón `^[A-Z0-9-]{2,20}$`, `name` de 3 a 200 caracteres, `campus` de 2 a 100; inserta o actualiza por `code` sin duplicar al repetir la carga; reporta filas inválidas sin abortar las válidas; audita `program.created` y `program.updated` con actor `system`) → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 3

- [ ] T099 [US3] Implementar `backend/src/saber_uli/identity/domain/profile.py` para que pase T095 → Qwen
  - Terminado: T095 en verde.
- [ ] T100 [US3] Implementar `backend/src/saber_uli/identity/infrastructure/repositories/programs.py`, `backend/src/saber_uli/identity/application/profile.py` y `backend/src/saber_uli/identity/api/profile_router.py` para que pase T096; agregar `listActivePrograms`, `getMyProfile`, `updateMyProfile` a `implemented_operations.py` → Qwen
  - Terminado: T096 y la prueba de contrato en verde.
- [ ] T101 [US3] Implementar `frontend/src/features/onboarding/ProfilePage.tsx` y `frontend/src/features/account/AccountPage.tsx` (edición del perfil) para que pase T097 → Qwen
  - Terminado: T097 en verde.
- [ ] T102 [US3] Implementar el comando `import-programs` en `backend/src/saber_uli/cli.py` y el caso de uso `backend/src/saber_uli/identity/application/import_programs.py` para que pase T098; documentado en quickstart.md §3 → Qwen
  - Terminado: T098 en verde.
- [ ] T103 [US3] Prueba e2e `frontend/tests/e2e/us3-first-login.spec.ts` (V1 de quickstart: ingreso, autorización y perfil hasta `/inicio` en menos de 60 s medidos por la prueba (SC-001); cerrar la app a mitad del primer ingreso y retomarlo en el paso pendiente (FR-022); editar el perfil) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T104 [US3] Revisión de US3 (T095–T103) en `specs/001-identidad-acceso/tasks.md`: FR-019 a FR-022 y SC-001 → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: MVP institucional completo (US1 + US2 + US3).

---

## Phase 6: User Story 4 - Acceso de invitados (Priority: P2)

**Goal**: un invitado entra con el enlace de su correo, sin contraseña; puede pedir enlaces de
ingreso nuevos; su acceso vence o se revoca de forma efectiva.

**Independent Test**: crear una invitación con el comando CLI, abrir el correo en Mailpit, pulsar
"Ingresar", verificar las restricciones y verificar que tras vencer no entra.

### Tests for User Story 4 ⚠️

- [ ] T105 [P] [US4] Prueba: acceso del invitado en `backend/tests/unit/identity/test_invitation_access.py` (aceptar crea un usuario `guest` solo con rol `guest` y pasa la invitación a `accepted`; acceso vigente si `accepted`, sin `revoked_at` y `access_expires_at` futuro; fin de acceso = mínimo entre revocación y vencimiento; vencido → `guest-access-expired`; revocado → `guest-access-revoked`) → Qwen
  - Terminado: la prueba falla.
- [ ] T106 [P] [US4] Prueba: enlaces de acceso en `backend/tests/unit/identity/test_access_links.py` (token de 256 bits; se guarda solo su SHA-256; un solo uso; vigencia `invitation` 7 días y `sign_in` 15 minutos tomadas de los parámetros; emitir uno nuevo invalida los anteriores sin usar del mismo propósito; research R-18 y R-19) → Opus
  - Terminado: la prueba falla.
- [ ] T107 [P] [US4] Prueba: `POST /api/auth/guest/sessions` en `backend/tests/integration/identity/test_guest_session_api.py` (token válido de invitación → crea invitado, abre sesión y fija la cookie; token usado o vencido → 400 `access-link-invalid`; acceso vencido → 403 `guest-access-expired`; revocado → 403 `guest-access-revoked`; 10/min por IP; escenarios 4.1, 4.3 y 4.4) → Opus
  - Terminado: la prueba falla.
- [ ] T108 [P] [US4] Prueba: `POST /api/auth/guest/link-requests` en `backend/tests/integration/identity/test_sign_in_link_request.py` (siempre 202 con el mismo cuerpo exista o no el correo (FR-013); solo un invitado vigente genera `identity.SignInLinkRequested`; el payload del outbox no contiene correo ni token; límites 5/h por hash de correo y 20/h por IP) → Opus
  - Terminado: la prueba falla.
- [ ] T109 [P] [US4] Prueba: manejador del worker en `backend/tests/integration/identity/test_sign_in_link_handler.py` (al procesar `SignInLinkRequested` emite el enlace, envía el correo a Mailpit con URL `<PUBLIC_BASE_URL>/acceso#t=<token>`, y el token en claro no aparece en base de datos, outbox, Redis ni logs) → Opus
  - Terminado: la prueba falla.
- [ ] T110 [P] [US4] Prueba: fachada para otros contextos en `backend/tests/unit/identity/test_public_facade.py` (`is_institutional(user_id)` y `is_guest(user_id)` para excluir invitados de ligas y analítica en specs futuras, FR-012) → Qwen
  - Terminado: la prueba falla.
- [ ] T111 [P] [US4] Prueba: comando `saber-uli identity invite-guest --email --days` en `backend/tests/integration/identity/test_cli_invite_guest.py` (crea invitación con actor `system`, rechaza dominios institucionales, encola `InvitationCreated`) → Qwen
  - Terminado: la prueba falla.
- [ ] T112 [P] [US4] Pruebas de componente `frontend/src/features/auth/GuestAccessPage.test.tsx` (lee el token del fragmento, lo borra del historial, solo envía al pulsar "Ingresar", mensajes por causa) y `frontend/src/features/auth/GuestLinkRequestPage.test.tsx` (mismo mensaje exista o no el correo) → Qwen
  - Terminado: las pruebas fallan.

### Implementation for User Story 4

- [ ] T113 [US4] Implementar `backend/src/saber_uli/identity/domain/invitation.py` (estado `sent → accepted` y reglas de acceso) para que pase T105 → Qwen
  - Terminado: T105 en verde.
- [ ] T114 [US4] Implementar `backend/src/saber_uli/identity/domain/access_link.py` y `backend/src/saber_uli/identity/infrastructure/link_tokens.py` para que pase T106 → Opus
  - Terminado: T106 en verde.
- [ ] T115 [US4] Implementar `backend/src/saber_uli/identity/application/guest_sessions.py` y `backend/src/saber_uli/identity/api/guest_router.py` (sesiones y solicitudes de enlace) para que pasen T107 y T108; agregar `createGuestSession` y `requestGuestSignInLink` a `implemented_operations.py` → Opus
  - Terminado: T107, T108 y la prueba de contrato en verde.
- [ ] T116 [US4] Implementar `backend/src/saber_uli/identity/infrastructure/handlers/link_emails.py` (manejadores de `SignInLinkRequested` e `InvitationCreated` que emiten el enlace y llaman a `notifications.application.public.send_email`) y las plantillas `backend/src/saber_uli/notifications/infrastructure/templates/{guest_invitation,guest_sign_in}.{html,txt}.j2` para que pase T109 → Opus
  - Terminado: T109 en verde.
- [ ] T117 [P] [US4] Implementar `backend/src/saber_uli/identity/application/public.py` (fachada pública) para que pase T110 → Qwen
  - Terminado: T110 en verde; `lint-imports` pasa.
- [ ] T118 [P] [US4] Implementar el comando `invite-guest` en `backend/src/saber_uli/cli.py` y `backend/src/saber_uli/identity/application/invitations.py` (creación mínima) para que pase T111 → Qwen
  - Terminado: T111 en verde.
- [ ] T119 [US4] Implementar `frontend/src/features/auth/GuestAccessPage.tsx` (`/acceso`) y `frontend/src/features/auth/GuestLinkRequestPage.tsx` (`/ingresar/invitado`) para que pase T112 → Qwen
  - Terminado: T112 en verde.
- [ ] T120 [US4] Prueba e2e `frontend/tests/e2e/us4-guest-access.spec.ts` (V5 y V6: invitación por CLI, correo en Mailpit, ingreso sin contraseña en menos de 2 minutos (SC-007), perfil de invitado, enlace reutilizado rechazado, nuevo enlace por correo, acceso vencido rechazado con fecha simulada) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T121 [US4] Revisión de US4 (T105–T120) en `specs/001-identidad-acceso/tasks.md`: manejo de tokens, enumeración de correos, límites y FR-007, FR-011 a FR-013 → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: invitados entran y salen de forma segura.

---

## Phase 7: User Story 5 - Gestión de invitaciones (Priority: P2)

**Goal**: administradores y docentes envían invitaciones individuales y por lote, las reenvían,
cambian su vencimiento y las revocan; cada docente gestiona solo las suyas.

**Independent Test**: invitación individual y lote con filas inválidas, duplicadas e
institucionales; revisar el reporte; revocar y comprobar que el invitado pierde el acceso.

### Tests for User Story 5 ⚠️

- [ ] T122 [P] [US5] Prueba: reglas de gestión en `backend/tests/unit/identity/test_invitation_management.py` (correo de `INSTITUTIONAL_EMAIL_DOMAINS` o sus subdominios → `institutional-email-not-invitable` (FR-008); docente con vencimiento mayor a `teacher_max_access_days` → `access-expiry-out-of-range`, administrador sin límite (FR-006a); sin vencimiento → `default_guest_access_days`; invitación vigente al mismo correo → `invitation-already-active`; reenviar solo si no está aceptada; revocar incrementa el `auth_epoch` del invitado; renovar dentro de 90 días desde el fin del acceso vuelve a `accepted` y limpia `retention_notice_sent_at`; invitado suprimido → `guest-erased`) → Qwen
  - Terminado: la prueba falla.
- [ ] T123 [P] [US5] Prueba: lotes en `backend/tests/unit/identity/test_invitation_batch.py` (CSV UTF-8 con encabezado `correo,nombre,vence`, fecha `AAAA-MM-DD`; JSON equivalente; más de 500 filas → `batch-too-large`; resultado por fila `valid`, `invalid_email`, `duplicate_in_file`, `already_invited`, `institutional_email`, `expiry_out_of_range`; el lote vence a las 24 h; validar 500 filas en menos de 2 s) → Qwen
  - Terminado: la prueba falla.
- [ ] T124 [P] [US5] Prueba: API de invitaciones en `backend/tests/integration/identity/test_invitations_api.py` (crear, listar con filtros `status`, `q` e `invited_by` (solo administrador), obtener, cambiar vencimiento, reenviar y revocar; un docente solo ve las suyas y las ajenas responden 404 (escenario 5.7); un estudiante recibe 403; todas exigen sesión privilegiada; cada acción audita `invitation.*`; revocar termina las sesiones abiertas del invitado (escenario 5.4)) → Qwen
  - Terminado: la prueba falla.
- [ ] T125 [P] [US5] Prueba: API de lotes en `backend/tests/integration/identity/test_invitation_batches_api.py` (`POST /api/v1/invitation-batches` con CSV y con JSON devuelve el reporte; `POST /{id}/confirmation` crea solo las válidas, encola un `InvitationCreated` por fila y audita `invitation_batch.confirmed`; confirmar dos veces o vencido → 409 `batch-not-pending`; un docente no ve lotes ajenos) → Qwen
  - Terminado: la prueba falla.
- [ ] T126 [P] [US5] Prueba: tarea `expire_invitations` en `backend/tests/integration/identity/test_expire_invitations_task.py` (`sent` con enlace vencido → `expired`; `accepted` con acceso vencido → `expired` e incremento de `auth_epoch`; idempotente; `last_delivery_status` refleja `queued`, `sent` o `failed` del manejador; una invitación nunca aceptada pierde `email` e `invitee_name` y sus `access_links` 90 días después de `revoked_at` si fue revocada o, si no, de `link_expires_at`, y se audita `invitation.contact_purged` (FR-034e)) → Qwen
  - Terminado: la prueba falla.
- [ ] T127 [P] [US5] Pruebas de componente `frontend/src/features/invitations/InvitationsPage.test.tsx` (lista con filtro por estado, acciones por fila, docente sin filtro `invited_by`), `InviteForm.test.tsx` (validación de correo y vencimiento máximo) y `BatchUpload.test.tsx` (carga de CSV, tabla del reporte por fila, confirmación) → Qwen
  - Terminado: las pruebas fallan.

### Implementation for User Story 5

- [ ] T128 [US5] Completar `backend/src/saber_uli/identity/domain/invitation.py` (reenviar, revocar, cambiar vencimiento, renovar) para que pase T122 → Qwen
  - Terminado: T122 en verde.
- [ ] T129 [US5] Implementar `backend/src/saber_uli/identity/domain/invitation_batch.py` y `backend/src/saber_uli/identity/application/invitation_batches.py` para que pase T123 → Qwen
  - Terminado: T123 en verde.
- [ ] T130 [US5] Completar `backend/src/saber_uli/identity/application/invitations.py` e implementar `backend/src/saber_uli/identity/api/invitations_router.py` (invitaciones y lotes, con alcance por `invited_by` en la consulta) para que pasen T124 y T125; agregar las 9 operaciones de invitaciones y lotes a `implemented_operations.py` → Qwen
  - Terminado: T124, T125 y la prueba de contrato en verde.
- [ ] T131 [US5] Implementar las tareas `expire_invitations` en `backend/src/saber_uli/identity/infrastructure/tasks.py` y el registro de `last_delivery_status` en `backend/src/saber_uli/identity/infrastructure/handlers/link_emails.py` (reenvío con `InvitationResent`), incluida la purga de contacto de FR-034e, para que pase T126 → Qwen
  - Terminado: T126 en verde.
- [ ] T132 [US5] Implementar `frontend/src/features/invitations/{InvitationsPage.tsx,InviteForm.tsx,BatchUpload.tsx,InvitationActions.tsx}` para que pase T127 → Qwen
  - Terminado: T127 en verde.
- [ ] T133 [US5] Prueba e2e `frontend/tests/e2e/us5-invitations.spec.ts` (V7 a V12 de quickstart: correo institucional rechazado, tope del docente, lote de 200 filas en menos de 5 minutos (SC-005), alcance del docente, revocación inmediata, renovación con progreso conservado) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T134 [US5] Revisión de US5 (T122–T133) en `specs/001-identidad-acceso/tasks.md`: alcance por docente sin fugas (404 en recursos ajenos), auditoría completa (SC-004), FR-006 a FR-010 → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: ciclo completo de invitados (US4 + US5).

---

## Phase 8: User Story 6 - Roles y grupos (Priority: P2)

**Goal**: el administrador asigna roles combinables, programas a directores, crea grupos con
estudiantes y docentes, desactiva cuentas, gestiona programas, parámetros y consulta auditoría.

**Independent Test**: asignar Docente y Director a un usuario, asociarlo a un grupo y verificar
la unión de permisos; retirar un rol y verificar que los pierde; intentar quitar el último
administrador.

### Tests for User Story 6 ⚠️

- [ ] T135 [P] [US6] Prueba: reglas de roles en `backend/tests/unit/identity/test_role_rules.py` (un institucional conserva siempre `student` (`student-role-required`); `guest` es exclusivo (`guest-role-exclusive`); `program_director` exige al menos un programa (`director-requires-programs`); retirar `admin` o desactivar al último administrador activo → `last-admin`; retirar roles incrementa `auth_epoch`) → Qwen
  - Terminado: la prueba falla.
- [ ] T136 [P] [US6] Prueba de concurrencia en `backend/tests/integration/identity/test_last_admin_concurrency.py` (dos administradores se quitan el rol mutuamente en transacciones simultáneas: exactamente una falla; FR-025) → Opus
  - Terminado: la prueba falla.
- [ ] T137 [P] [US6] Prueba: API de usuarios en `backend/tests/integration/identity/test_admin_users_api.py` (listar con filtros `q`, `kind`, `role` y `status`; obtener; `PATCH` de estado desactiva, termina sesiones y audita `user.disabled|reactivated`; `PUT /roles` audita `user.role_granted|role_revoked` con roles antes y después y `user.director_programs_changed`; solo administradores con sesión privilegiada) → Qwen
  - Terminado: la prueba falla.
- [ ] T138 [P] [US6] Prueba: grupos en `backend/tests/unit/identity/test_group.py` (miembros solo estudiantes institucionales (`not-institutional-student`), docentes solo con rol `teacher` (`not-a-teacher`), nombre de 2 a 120 caracteres, `cohort_label` hasta 20) y `backend/tests/integration/identity/test_groups_api.py` (CRUD y archivado, agregar y quitar miembros y docentes, auditoría `group.*`) → Qwen
  - Terminado: las pruebas fallan.
- [ ] T139 [P] [US6] Prueba: vista del docente y del director en `backend/tests/integration/identity/test_teacher_groups_api.py` (`GET /api/v1/teacher/groups` solo grupos propios; `GET /teacher/groups/{id}/students` devuelve `display_name` sin correo y 404 en grupos ajenos (FR-027); un usuario solo `program_director` recibe 403 en endpoints que exponen nombres o correos (FR-026); la fachada `director_program_ids(user_id)` devuelve sus programas) → Opus
  - Terminado: la prueba falla.
- [ ] T140 [P] [US6] Prueba: programas, parámetros y auditoría en `backend/tests/integration/identity/test_admin_catalogs_api.py` (programas: `code` con patrón `^[A-Z0-9-]{2,20}$` único, `name` 3–200, `campus` 2–100, auditoría `program.*`; parámetros: rangos del contrato y auditoría `setting.changed`; auditoría: filtros `action`, `actor_id`, `subject_user_id`, `from`, `to` y orden descendente, solo lectura) → Qwen
  - Terminado: la prueba falla.
- [ ] T141 [P] [US6] Prueba: comando `saber-uli identity grant-admin --email` en `backend/tests/integration/identity/test_cli_grant_admin.py` (solo sobre un institucional existente; audita con actor `system`; mensaje claro si no existe) → Qwen
  - Terminado: la prueba falla.
- [ ] T142 [P] [US6] Pruebas de componente en `frontend/src/features/admin/UsersPage.test.tsx` (lista, editor de roles con programas del director, desactivar y reactivar, error `last-admin`), `frontend/src/features/admin/GroupsPage.test.tsx`, `frontend/src/features/admin/CatalogPages.test.tsx` (programas, parámetros, auditoría) y `frontend/src/features/teacher/TeacherGroupsPage.test.tsx` (nombres sin correo) → Qwen
  - Terminado: las pruebas fallan.

### Implementation for User Story 6

- [ ] T143 [US6] Completar `backend/src/saber_uli/identity/domain/user.py` (asignación de roles y programas del director) y el bloqueo de administradores en `backend/src/saber_uli/identity/infrastructure/repositories/users.py` para que pasen T135 y T136 → Qwen
  - Terminado: T135 y T136 en verde (T136 revisada por Opus).
- [ ] T144 [US6] Implementar `backend/src/saber_uli/identity/application/admin_users.py` y `backend/src/saber_uli/identity/api/admin_users_router.py` para que pase T137 → Qwen
  - Terminado: T137 en verde.
- [ ] T145 [US6] Implementar `backend/src/saber_uli/identity/domain/group.py`, `backend/src/saber_uli/identity/application/groups.py`, `backend/src/saber_uli/identity/api/groups_router.py` y `backend/src/saber_uli/identity/api/teacher_router.py`, y `director_program_ids` en `backend/src/saber_uli/identity/application/public.py`, para que pasen T138 y T139 → Qwen
  - Terminado: T138 y T139 en verde.
- [ ] T146 [US6] Implementar `backend/src/saber_uli/identity/api/admin_catalogs_router.py` (programas, parámetros, auditoría) con sus casos de uso en `backend/src/saber_uli/identity/application/catalogs.py` para que pase T140; agregar las operaciones de usuarios, grupos, docente, programas, parámetros y auditoría a `implemented_operations.py` → Qwen
  - Terminado: T140 y la prueba de contrato en verde.
- [ ] T147 [US6] Implementar el comando `grant-admin` en `backend/src/saber_uli/cli.py` para que pase T141 → Qwen
  - Terminado: T141 en verde.
- [ ] T148 [P] [US6] Implementar `frontend/src/features/admin/{UsersPage.tsx,UserRolesEditor.tsx,GroupsPage.tsx,GroupDetail.tsx}` para que pasen sus pruebas de T142 → Qwen
  - Terminado: pruebas de usuarios y grupos en verde.
- [ ] T149 [P] [US6] Implementar `frontend/src/features/admin/{ProgramsPage.tsx,SettingsPage.tsx,AuditPage.tsx}` y `frontend/src/features/teacher/TeacherGroupsPage.tsx` para que pasen sus pruebas de T142 → Qwen
  - Terminado: pruebas de catálogos y docente en verde.
- [ ] T150 [US6] Prueba e2e `frontend/tests/e2e/us6-roles-groups.spec.ts` (V13 a V15: unión de permisos, último administrador, vista del docente y del director, reautenticación tras 31 minutos de inactividad privilegiada sin interrumpir la práctica personal) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T151 [US6] Revisión de US6 (T135–T150) en `specs/001-identidad-acceso/tasks.md`: autorización y alcance (FR-023 a FR-030), datos visibles por rol, auditoría (SC-004) → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: roles, grupos y administración completos.

---

## Phase 9: User Story 7 - Supresión de la cuenta y de los datos personales (Priority: P3)

**Goal**: el usuario solicita la supresión y pierde el acceso al instante; se completa en máximo
15 días hábiles; los invitados (90 días) e institucionales (1 año sin ingresar) se suprimen
automáticamente con aviso 30 días antes.

**Independent Test**: solicitar la supresión, confirmar, verificar que no puede ingresar, que sus
datos personales no aparecen y que todo quedó auditado; reingresar crea una cuenta nueva.

### Tests for User Story 7 ⚠️

- [ ] T152 [P] [US7] Prueba: días hábiles en `backend/tests/unit/identity/test_business_days.py` (15 días hábiles en Colombia excluyendo sábados, domingos y festivos de `holidays` CO, incluidos los trasladados por la Ley Emiliani; casos que cruzan Semana Santa y fin de año) → Qwen
  - Terminado: la prueba falla.
- [ ] T153 [P] [US7] Prueba: política de conservación en `backend/tests/unit/identity/test_retention_policy.py` (invitado: fin = mínimo(revocado_en, vence_en), aviso en fin + 60 días y supresión en fin + 90; institucional: aviso en `last_login_at` + 335 días y supresión en + 365; ingresar o renovar mueve las fechas y cancela; el aviso no se repite si `retention_notice_sent_at` existe; FR-034a, FR-034b, FR-034c) → Qwen
  - Terminado: la prueba falla.
- [ ] T154 [P] [US7] Prueba: solicitud en `backend/tests/integration/identity/test_deletion_request_api.py` (`POST /api/v1/me/deletion-request` exige `confirmation` = `ELIMINAR`; responde 202, pasa a `deletion_pending`, incrementa `auth_epoch` y la siguiente petición responde 401; `due_date` a 15 días hábiles; segunda solicitud → 409 `deletion-already-requested`; el último administrador activo recibe 409 `last-admin` y su cuenta no cambia (FR-034d, escenario 7.5); exenta de autorización de datos; audita `deletion.requested`; `GET /api/v1/admin/deletion-requests` con filtro de estado) → Qwen
  - Terminado: la prueba falla.
- [ ] T155 [P] [US7] Prueba: borrado en `backend/tests/integration/identity/test_erase_user.py` (deja la lápida con `status='deleted'` y sin nombre, correo ni `oid`; borra perfil, roles, programas del director, membresías, sesiones, enlaces y correo de invitaciones; conserva `consents` y `audit_events` solo con el UUID; publica `identity.UserErased`; idempotente si se reanuda; tras borrar, ingresar con el mismo `oid` crea una cuenta nueva sin historial (escenario 7.3); revisión automática de que ninguna fila del esquema `identity` contiene el correo o el nombre borrados; FR-033) → Opus
  - Terminado: la prueba falla.
- [ ] T156 [P] [US7] Prueba: tareas programadas en `backend/tests/integration/identity/test_retention_tasks.py` (`process_retention` con `FixedClock`: encola `RetentionNoticeDue` y envía el aviso a Mailpit 30 días antes con la fecha y cómo evitarlo; en la fecha crea la solicitud con origen `guest_retention` o `institutional_retention`; si el correo falla, la supresión sigue; `process_deletion_requests` completa solicitudes y audita `deletion.completed` y `retention.notice_sent`; el último administrador activo con más de 1 año sin ingresar no recibe solicitud de supresión y se audita `retention.skipped_last_admin` (FR-034d); SC-006) → Qwen
  - Terminado: la prueba falla.
- [ ] T157 [P] [US7] Pruebas de componente `frontend/src/features/account/DeleteAccountSection.test.tsx` (explica qué se borra y qué se conserva anónimo; exige escribir ELIMINAR; tras confirmar cierra la sesión) y `frontend/src/features/admin/DeletionRequestsPage.test.tsx` (estado y fecha límite) → Qwen
  - Terminado: las pruebas fallan.

### Implementation for User Story 7

- [ ] T158 [P] [US7] Implementar `backend/src/saber_uli/identity/domain/business_days.py` para que pase T152 → Qwen
  - Terminado: T152 en verde.
- [ ] T159 [P] [US7] Implementar `backend/src/saber_uli/identity/domain/retention.py` para que pase T153 → Qwen
  - Terminado: T153 en verde.
- [ ] T160 [US7] Implementar `backend/src/saber_uli/identity/application/deletion.py` y `backend/src/saber_uli/identity/api/deletion_router.py` para que pase T154; agregar `getMyDeletionRequest`, `requestMyDeletion` y `adminListDeletionRequests` a `implemented_operations.py` → Qwen
  - Terminado: T154 y la prueba de contrato en verde.
- [ ] T161 [US7] Implementar `backend/src/saber_uli/identity/application/erase_user.py` para que pase T155 → Opus
  - Terminado: T155 en verde.
- [ ] T162 [US7] Implementar `process_retention` y `process_deletion_requests` en `backend/src/saber_uli/identity/infrastructure/tasks.py`, el manejador `backend/src/saber_uli/identity/infrastructure/handlers/retention_notice.py` y las plantillas `backend/src/saber_uli/notifications/infrastructure/templates/retention_notice_{guest,institutional}.{html,txt}.j2` para que pase T156 → Qwen
  - Terminado: T156 en verde.
- [ ] T163 [US7] Implementar `frontend/src/features/account/DeleteAccountSection.tsx` y `frontend/src/features/admin/DeletionRequestsPage.tsx` para que pase T157 → Qwen
  - Terminado: T157 en verde.
- [ ] T164 [US7] Prueba e2e `frontend/tests/e2e/us7-deletion.spec.ts` (V18: solicitud, cierre inmediato, solicitud visible para el administrador, procesamiento por el worker, reingreso como cuenta nueva) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T165 [US7] Revisión de US7 (T152–T164) en `specs/001-identidad-acceso/tasks.md`: que no queden datos personales tras la supresión, plazos de la Ley 1581, FR-032 a FR-034c y SC-006 → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: derechos de supresión y conservación automáticos operativos.

---

## Phase 10: User Story 8 - Consulta y rectificación de mis datos (Priority: P3)

**Goal**: el usuario ve y descarga todos sus datos personales, y sabe cómo corregir los que
vienen del directorio institucional.

**Independent Test**: abrir "Mis datos", ver el listado completo, descargar la copia y corregir un
dato editable del perfil.

### Tests for User Story 8 ⚠️

- [ ] T166 [P] [US8] Prueba: exportación en `backend/tests/integration/identity/test_data_export.py` (`GET /api/v1/me/data-export` con `Content-Disposition: attachment`; contiene identidad, perfil, roles, nombres de grupos, historial de autorizaciones, invitación (solo invitados) y `source_note`; nunca incluye datos de otras personas; las secciones de otros contextos se agregan por el registro de proveedores; FR-031) → Qwen
  - Terminado: la prueba falla.
- [ ] T167 [P] [US8] Prueba de componente `frontend/src/features/account/MyDataPage.test.tsx` (muestra los datos, botón de descarga, nota de rectificación en el directorio para institucionales (escenario 8.2), enlace a editar perfil) → Qwen
  - Terminado: la prueba falla.

### Implementation for User Story 8

- [ ] T168 [US8] Implementar `backend/src/saber_uli/shared/application/data_export_registry.py`, `backend/src/saber_uli/identity/application/data_export.py` y la ruta en `backend/src/saber_uli/identity/api/me_router.py` para que pase T166; agregar `exportMyData` a `implemented_operations.py` → Qwen
  - Terminado: T166 y la prueba de contrato en verde.
- [ ] T169 [US8] Implementar `frontend/src/features/account/MyDataPage.tsx` (`/mi-cuenta/datos`, junto con la sección de T163) para que pase T167 → Qwen
  - Terminado: T167 en verde.
- [ ] T170 [US8] Prueba e2e `frontend/tests/e2e/us8-my-data.spec.ts` (V17: ver, descargar y validar el JSON; editar un dato del perfil) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T171 [US8] Revisión de US8 (T166–T170) en `specs/001-identidad-acceso/tasks.md`: completitud de la exportación frente a data-model.md y FR-031 → Opus
  - Terminado: tareas aprobadas y marcadas.

**Checkpoint**: las 8 historias están completas.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: verificaciones transversales y Definición de Terminado (kit, sección 9).

- [ ] T172 [P] Prueba e2e de uso sin conexión `frontend/tests/e2e/offline-access.spec.ts` (V16: app instalada en modo avión funciona hasta el día 7 con el reloj de Playwright; el día 8 pide reconectarse; al reconectar con acceso revocado no sincroniza y muestra la causa; FR-038, FR-039) → Qwen
  - Terminado: pasa contra el stack `e2e`.
- [ ] T173 [P] Prueba e2e de accesibilidad `frontend/tests/e2e/a11y.spec.ts` (axe nivel WCAG 2.2 AA en todas las rutas de research R-35, en viewport móvil, con navegación por teclado y foco visible) → Qwen
  - Terminado: cero infracciones.
- [ ] T174 [P] Configurar Lighthouse CI en `frontend/lighthouserc.json` (rendimiento ≥ 90 en `/ingresar`, criterios de PWA instalable, sin errores de consola) → Qwen
  - Terminado: el trabajo `lighthouse` de CI pasa.
- [ ] T175 [P] Prueba de registros `backend/tests/integration/test_no_pii_in_logs.py` (ejecuta los flujos de US1 a US8 capturando los logs de API y worker y verifica que no aparecen correos, nombres ni tokens; V21) → Opus
  - Terminado: la prueba pasa.
- [ ] T176 [P] Prueba de presupuesto de rendimiento `backend/tests/integration/identity/test_performance_budgets.py` (p95 < 300 ms en `/api/v1/me`, `/api/auth/refresh` e invitaciones con 200 peticiones concurrentes sobre datos de 40 000 usuarios sembrados; validación de lote de 500 filas < 2 s) → Qwen
  - Terminado: los presupuestos se cumplen o se registra una decisión pendiente con mediciones.
- [ ] T177 Ejecutar Schemathesis completo con las 51 operaciones en `backend/tests/contract/implemented_operations.py` → Qwen
  - Terminado: cero fallos; la lista coincide con todos los `operationId` del contrato.
- [ ] T178 Escribir la verificación ASVS 4.0.3 nivel 2 de la funcionalidad en `docs/security/asvs-001-identidad.md` (requisitos aplicables de V2, V3, V4, V5, V7, V8, V13 con evidencia o justificación, incluida la desviación de V3.3.2 registrada en plan.md) → Opus
  - Terminado: documento completo; ningún requisito aplicable sin evidencia.
- [ ] T179 [P] Escribir `README.md` en la raíz (qué es Saber Uli, cómo levantar el entorno con enlace a quickstart.md, estructura, flujo SDD con dos modelos) → Qwen
  - Terminado: un recién llegado levanta el stack siguiendo solo el README y el quickstart.
- [ ] T180 Validar de punta a punta los escenarios V1 a V21 de `specs/001-identidad-acceso/quickstart.md` sobre `docker compose up` desde cero, corregir la documentación si algo difiere y confirmar la Definición de Terminado del kit (sección 9) → Opus
  - Terminado: todos los escenarios pasan; cobertura ≥ 80 % en `domain` y `application`; CI en verde; `/speckit.analyze` sin inconsistencias abiertas.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de la fase 1 y **bloquea todas las historias**. T070 (revisión de
  seguridad) cierra la fase.
- **Historias (fases 3 a 10)**: dependen solo de la fase 2. Orden recomendado por prioridad:
  US1 → US2 → US3 (P1, MVP) → US4 → US5 → US6 (P2) → US7 → US8 (P3).
- **Polish (fase 11)**: depende de las historias que se quieran entregar; T180 requiere todas.

### User Story Dependencies

| Historia | Depende de | Nota de independencia |
|----------|------------|-----------------------|
| US1 | Fase 2 | Ninguna otra historia |
| US2 | Fase 2 | La guardia de consentimiento (T051–T052) ya está en la fase 2; sus pruebas crean usuarios con fábricas |
| US3 | Fase 2 | Los programas de prueba se crean con fábricas; la gestión de programas llega en US6 |
| US4 | Fase 2 | Las invitaciones se crean con el comando CLI de T118, sin depender de la API de US5 |
| US5 | Fase 2, T113–T114 y T116 de US4 | Reutiliza el agregado `Invitation`, los enlaces y el manejador de correo de US4 |
| US6 | Fase 2 | Ninguna otra historia |
| US7 | Fase 2 | Las reglas de invitados (FR-034a) usan fechas de invitación creadas con fábricas |
| US8 | Fase 2 | La sección de supresión de `/mi-cuenta/datos` (US7) se integra si existe |

### Within Each User Story

- Las pruebas se escriben primero y deben fallar (principio IV).
- Dominio → aplicación → API → frontend → e2e → revisión de Opus.
- Una historia se cierra cuando su tarea de revisión está aprobada.

### Parallel Opportunities

- Fase 1: T003–T006, T013 y T015 en paralelo tras T001–T002; T007 (prueba de infraestructura)
  va antes de T008–T012 y T014, que después pueden avanzar en paralelo.
- Fase 2: todas las pruebas marcadas [P] en paralelo; las implementaciones se encadenan con su prueba.
  El frontend (T060–T069) avanza en paralelo con el backend.
- Tras la fase 2: US1, US2, US3, US4, US6 y US7 pueden avanzar en paralelo; US5 espera a T113–T116.
- Dentro de cada historia: todas las pruebas [P] en paralelo.

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 en paralelo (primero; deben fallar):
Task: "T071 Prueba del caso de uso en backend/tests/unit/identity/test_authenticate_institutional_user.py"   # Qwen
Task: "T072 Prueba del adaptador Entra ID en backend/tests/integration/identity/test_entra_adapter.py"       # Opus
Task: "T073 Prueba del flujo HTTP en backend/tests/integration/identity/test_microsoft_login_flow.py"        # Opus
Task: "T074 Prueba de /api/v1/me en backend/tests/integration/identity/test_me.py"                          # Qwen
Task: "T075 Prueba de LoginPage en frontend/src/features/auth/LoginPage.test.tsx"                           # Qwen

# Luego, implementaciones en paralelo entre backend y frontend:
Task: "T076 AuthenticateInstitutionalUser"  +  Task: "T080 LoginPage y bootstrap"
```

## Parallel Example: User Story 5

```bash
Task: "T122 Reglas de gestión de invitaciones"
Task: "T123 Lotes de invitaciones"
Task: "T124 API de invitaciones"
Task: "T125 API de lotes"
Task: "T126 Tarea expire_invitations"
Task: "T127 Componentes de /invitaciones"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Fase 1: Setup.
2. Fase 2: Foundational (incluye la revisión de seguridad T070).
3. Fases 3–5: US1, US2 y US3.
4. **Parar y validar**: quickstart V1–V4; un estudiante institucional entra, autoriza y completa
   su perfil en menos de 1 minuto. Es el mínimo necesario para que la spec 003 conecte la
   primera lección.

### Incremental Delivery

1. MVP institucional (US1–US3) → demo.
2. Invitados (US4 + US5) → demo.
3. Administración (US6) → demo.
4. Derechos del titular (US7 + US8) → demo; requisito antes de producción.
5. Polish (fase 11) → Definición de Terminado.

### Reparto entre modelos

| Modelo | Tareas | Total |
|--------|--------|-------|
| Opus (diseño, seguridad, revisión) | T003, T010, T011, T015, T018, T019, T029, T030, T035, T036, T039, T040, T045–T050, T062, T063, T070, T072, T073, T077, T078, T082, T087, T094, T104, T106–T109, T114–T116, T121, T134, T136, T139, T151, T155, T161, T165, T171, T175, T178, T180 | 48 |
| Qwen (implementación) | Todas las demás | 132 |

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Las etiquetas [USn] permiten rastrear cada tarea a su historia.
- Verificar que cada prueba falla antes de implementar.
- Un commit por tarea (Conventional Commits, por ejemplo `feat(identity): …`, `test(identity): …`).
- Ninguna tarea cambia `contracts/openapi.yaml`, `data-model.md` ni los ADR; cualquier cambio de
  diseño pasa primero por Opus y por la especificación (principio I).
- Antes de implementar, crear la rama `001-identidad-acceso` (el repositorio sigue en `master`).
