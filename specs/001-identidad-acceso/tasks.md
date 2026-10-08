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
  - Cambio de Opus (2026-10-06): nuevo contrato `aplicacion-sin-frameworks` (la capa
    `application` de cada contexto no importa FastAPI, Starlette, SQLAlchemy, asyncpg, Celery,
    Redis, httpx, Authlib, Jinja2 ni `saber_uli.config`). Verificado: 5 KEPT, y BROKEN con un
    `import sqlalchemy` de prueba en `shared/application` (revertido).
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
- [x] T006 [P] Crear `.pre-commit-config.yaml` con ruff, ruff-format, mypy (backend), eslint y prettier (frontend), detección de secretos (`detect-secrets`) y verificación de Conventional Commits (`commitizen`) → Qwen
  - Terminado: `pre-commit run --all-files` pasa; un mensaje de commit sin formato convencional es rechazado.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos.
    `.pre-commit-config.yaml`: ruff, ruff format y mypy `--strict` (backend) y eslint y prettier
    (frontend) como ganchos locales con las versiones fijadas del proyecto (`uv`, `npm`);
    detect-secrets 1.5.0 contra `.secrets.baseline` (seis hallazgos revisados: contraseña de
    ejemplo de `.env.example`, sumas de comprobación de `.specify`, valores ficticios de
    `test_config.py` y el nombre de variable de `01-roles.sql`; rutas normalizadas con `/` para
    que la línea base sirva en Linux); commitizen 4.19.1 en `commit-msg`. Verificado:
    `uvx pre-commit run --all-files` pasa y un mensaje sin formato convencional es rechazado
    (uno convencional pasa). Instalación local: `uvx pre-commit install`.
- [x] T007 Prueba de infraestructura en `backend/tests/infra/test_containers.py` (sin dependencias nuevas: CLI de Docker por `subprocess`; se omite con `pytest.mark.skipif` si Docker no está disponible): `docker compose config` válido para `compose.yaml` + override y + prod; la imagen del backend corre con UID 10001; tras `docker compose up -d --wait` todos los servicios están `healthy` y `migrate` sale con código 0; `curl -I` al proxy muestra `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` y, para `sw.js`, `Service-Worker-Allowed: /`; `docker compose top` no muestra ningún proceso principal con UID 0; en `db` existen los roles `saber_migrator`, `saber_app` y `saber_bi` y las extensiones `citext` y `pg_stat_statements`; `actionlint` valida `.github/workflows/ci.yml` y el flujo contiene los trabajos `infra`, `backend-quality`, `backend-tests`, `contract`, `frontend-quality`, `e2e`, `lighthouse`, `build` y `security`. Si Docker no está disponible la prueba se omite, salvo con `REQUIRE_DOCKER=1`, en cuyo caso falla (constitución IV y X, research R-32 y R-33) → Qwen
  - Terminado: la prueba existe y falla porque aún no hay Dockerfiles, Compose, Nginx, scripts de inicio de Postgres ni flujo de CI.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos; falló completa
    antes de T008–T013 (commit `925e60c`). Detección de Docker compartida en
    `backend/tests/_docker.py`. Marcadores `infra` (fuera de la ejecución por defecto; se corre
    con `pytest -m infra tests/infra`) y `full_stack`. Con T008, T009, T012 y T013:
    `pytest -m "infra and not full_stack"` da 9 en verde (Compose válido ×3, UID 10001, cabeceras,
    `sw.js`, ningún proceso principal con UID 0, roles y extensiones, `.env.example` cubierto).
    Pendientes (`full_stack`): servicios `api`/`worker`/`beat`/`migrate` (T026, T034, T058) y CI
    (T014). El análisis de `docker compose top` sigue el formato de tabla de Compose v5.
- [x] T008 [P] Crear `backend/Dockerfile` multi-etapa (builder con uv; runtime `python:3.13-slim`, usuario no root UID 10001, sin herramientas de compilación) con comandos para `api` (uvicorn, 4 workers), `worker` (celery worker), `beat` (celery beat con archivo de latido en `/tmp/beat-heartbeat`) y `migrate` (`saber-uli migrate`) → Qwen
  - Terminado: `docker build` funciona; `docker run --rm <img> id -u` devuelve 10001; la parte de imagen de T007 pasa.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos. Builder con
    `ghcr.io/astral-sh/uv:0.11` (`uv sync --frozen --no-dev`, caché de BuildKit); runtime
    `python:3.13-slim` con usuario `saber` UID/GID 10001, sin compiladores, entorno virtual y
    migraciones de solo lectura (propiedad de root), `SABER_MIGRATIONS_DIR=/app/migrations`.
    Los cuatro servicios salen de `infra/docker/backend-entrypoint.sh` (`api`, `worker`, `beat`,
    `migrate`; cualquier otro comando se ejecuta tal cual, por ejemplo `saber-uli grant-admin`),
    siempre con `exec`. `api` usa `saber_uli.main:app` con 4 workers (`API_WORKERS`) y sin
    `--log-config`: cada worker llama a `configure_logging`. Verificado: `id -u` = 10001; imagen
    de 380 MB; `migrate` y `api` fallan solo porque faltan `cli.py` (T026) y `main.py` (T058).
    `alembic.ini` no se copia: `run_migrations` arma la configuración por código (lote 04).
- [x] T009 [P] Crear `frontend/Dockerfile` multi-etapa (build con Node 24; final `nginxinc/nginx-unprivileged` que copia `dist/` y `infra/nginx/`) → Qwen
  - Terminado: la imagen sirve `index.html` en el puerto 8080 sin root; la imagen corre sin UID 0 según T007.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos. Build con
    `node:24-alpine` (`npm ci` con caché y `npm run build`); final
    `nginxinc/nginx-unprivileged:1.29-alpine` (UID 101, puerto 8080) con la disposición de
    `infra/nginx/default.conf`. Verificado: `nginx -t` correcto; `/` con CSP sin `unsafe-inline`
    en `script-src`, `nosniff`, `no-referrer` y `DENY`; `/sw.js` (404 hasta T068) con
    `Service-Worker-Allowed: /` y `no-cache`; fallback SPA a `index.html`.
- [x] T010 [P] Escribir la configuración de Nginx en `infra/nginx/default.conf` y `infra/nginx/security-headers.conf`: proxy de `/api/` a `api:8000`; `sw.js` y `manifest.webmanifest` con `Cache-Control: no-cache` y `Service-Worker-Allowed: /`; fallback SPA a `index.html`; cabeceras `Content-Security-Policy` (sin `unsafe-inline` en `script-src`, `connect-src 'self'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` restrictiva, `X-Frame-Options: DENY`; HSTS solo en `infra/nginx/tls.conf` para producción (research R-33) → Opus
  - Estado: implementada por Opus en `infra/nginx/{default.conf,locations.conf,security-headers.conf,tls.conf}`; falta verificarla en contenedor con T007.
  - Nota para T009: copiar `default.conf` a `/etc/nginx/conf.d/default.conf` y los demás archivos de `infra/nginx/` a `/etc/nginx/saber/` (no a `conf.d/`, porque Nginx incluye todo `conf.d/*.conf` en el contexto http).
  - Nota para T012: en `compose.prod.yaml`, montar `infra/nginx/tls.conf` sobre `/etc/nginx/conf.d/default.conf` y los certificados en `/etc/nginx/certs/{fullchain.pem,privkey.pem}`; puertos 80→8080 y 443→8443. `api` debe arrancar Uvicorn con `--proxy-headers --forwarded-allow-ips` limitado a la red de Compose, para que los límites por IP (T035) usen la IP real.
  - Nota para T068: registrar el service worker con `injectRegister: 'script'` (la CSP no admite scripts en línea).
  - Terminado: `nginx -t` pasa en el contenedor; la parte de cabeceras de T007 pasa; `/api/health` llega a la API.
  - Verificada (2026-10-06): T007 en verde sobre la imagen del proxy (CSP sin `unsafe-inline` en
    `script-src`, `nosniff`, `no-referrer`, `DENY`, `Service-Worker-Allowed` en `sw.js`).
- [x] T011 [P] Crear `infra/postgres/init/01-roles.sql` y `02-extensions.sql`: roles `saber_migrator` (DDL), `saber_app` (DML), `saber_bi` (solo lectura de `analytics`, sin objetos aún) con contraseñas desde variables de entorno; extensiones `citext` y `pg_stat_statements` (research R-07) → Opus
  - Estado: implementada por Opus en `infra/postgres/init/{01-roles.sql,02-extensions.sql}`; falta verificarla en contenedor con T007 y T029.
  - Nota para T012 y T013: el servicio `db` necesita `SABER_MIGRATOR_PASSWORD`, `SABER_APP_PASSWORD` y `SABER_BI_PASSWORD` (mínimo 16 caracteres; sin ellas el contenedor no arranca) y el comando `postgres -c shared_preload_libraries=pg_stat_statements`. T024 debe pasar las mismas variables al contenedor de Testcontainers.
  - Terminado: la parte de roles y extensiones de T007 pasa al iniciar `db` desde cero; el superusuario no se usa en ningún otro servicio.
  - Verificada (2026-10-06): T007 (roles y extensiones en el contenedor `db`) y T029 (permisos
    por rol) en verde.
- [x] T012 Crear `compose.yaml` (servicios `proxy`, `api`, `worker`, `beat`, `migrate`, `db` con volumen en `/var/lib/postgresql`, `redis`), `compose.override.yaml` (recarga en caliente, `mailpit`, puertos locales) y `compose.prod.yaml` (TLS, `tls.conf`, sin mailpit); perfil `e2e` con `oidc` (`ghcr.io/navikt/mock-oauth2-server`, configuración en `infra/docker/mock-oauth2.json` con un emisor del inquilino válido y otro externo) y `mailpit`; `user:` explícito sin privilegios en `mailpit` y `oidc`; health checks y `depends_on` según la tabla de servicios de plan.md → Qwen
  - Terminado: T007 pasa completa (Compose válido, servicios `healthy`, `migrate` con código 0 y ningún proceso principal con UID 0).
  - Nota de Opus (2026-10-06): secuencia. T012 necesita antes T008, T009 y T013. Su verificación
    se hace en dos tiempos: al entregarla, `docker compose config` es válido en las tres
    combinaciones y `db`, `redis`, `proxy`, `mailpit` y `oidc` quedan `healthy`, con las pruebas de
    T007 de cabeceras, roles, extensiones y UID en verde sobre esos servicios. Las comprobaciones de
    `api`, `worker`, `beat` y `migrate` dependen de T026, T034 y T058, y T007 completa se exige al
    cerrar T058.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos. Primer tiempo de
    la verificación cumplido (ver T007). Imagen única del backend (`x-backend`) con
    `read_only`, `tmpfs /tmp`, `no-new-privileges` y `cap_drop: ALL`; `migrate` recibe solo
    `MIGRATION_DATABASE_URL` (mínimo privilegio) y `api`/`worker`/`beat` el entorno de la app con
    `DATABASE_URL` de `saber_app`, ambas armadas desde las contraseñas del `.env`. `db` con
    health check por TCP (no queda sano hasta terminar los scripts de inicio). Redis sin
    persistencia. `mailpit` (UID 65534) y `oidc` (UID 65532, `mock-oauth2-server:3.0.3`) en el
    perfil `e2e`; el override activa Mailpit con `profiles: !reset []`, publica puertos solo en
    127.0.0.1 y da recarga en caliente con `backend/src` montado y `PYTHONPATH`. Prod monta
    `tls.conf` y los certificados y publica 80/443. El health check de `oidc` usa GET: el
    servidor no responde a HEAD. `infra/docker/mock-oauth2.json` con los emisores
    `1111…` (inquilino) y `2222…` (externo).
  - Decisión resuelta en T069: el navegador y la API usan el mismo emisor `http://oidc:8080`
    (simulador publicado en `127.0.0.1:8080:8080` y `127.0.0.1 oidc` en el archivo hosts).
  - Nota: Redis no tiene contraseña; solo es accesible en la red interna de Compose (no se
    publica en ningún archivo). Revisar en T070.
- [x] T013 [P] Crear `.env.example` documentado: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_AUTHORITY`, `PUBLIC_BASE_URL`, `INSTITUTIONAL_EMAIL_DOMAINS`, `JWT_SIGNING_KEY`, `JWT_KEY_ID`, `SESSION_COOKIE_SECRET`, `DATABASE_URL` (por rol), `REDIS_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `OTEL_ENABLED`, `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` (reservadas para la spec 009), contraseñas de roles de base de datos → Qwen
  - Terminado: cada variable tiene comentario en español; ningún valor real; `.env` está en `.gitignore`.
  - Nota de Opus (2026-10-06): los nombres definitivos de las variables están en
    `handoffs/qwen-02-T016-T017-T022-T023.md` (tabla de T016); incluye `MIGRATION_DATABASE_URL`,
    `SMTP_STARTTLS` y `LOG_LEVEL`.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos. Variables de la
    tabla del lote 02 más las que solo usa Compose (`POSTGRES_DB`, `POSTGRES_PASSWORD`,
    `SABER_*_PASSWORD`) y `E2E_EXTERNAL_TENANT_ID`. `DATABASE_URL`, `MIGRATION_DATABASE_URL`,
    `REDIS_URL` y `ENTRA_AUTHORITY` quedan comentadas: Compose las arma (las contraseñas no se
    repiten) y solo se definen para ejecutar fuera de Docker. Valores de ejemplo sin secretos
    reales; `.env` ignorado y `.env.example` versionado. La prueba de T007 que compara
    `.env.example` con el entorno de prueba está en verde.
- [x] T014 [P] Crear `.github/workflows/ci.yml` con los trabajos `infra` (`pytest backend/tests/infra`), `backend-quality` (ruff, mypy, lint-imports), `backend-tests` (pytest con cobertura y `fail_under`), `contract` (Schemathesis), `frontend-quality` (lint, typecheck, vitest, verificación de que `npm run api:generate` no deja cambios), `e2e` (compose perfil `e2e` + Playwright), `lighthouse`, `build` (imágenes) y `security` (Trivy sobre imágenes y sistema de archivos, falla con severidad CRITICAL/HIGH); y `.github/dependabot.yml` para pip, npm, docker y actions → Qwen
  - Terminado: la parte de CI de T007 pasa; el trabajo `infra` ejecuta `pytest backend/tests/infra` con `REQUIRE_DOCKER=1`; los trabajos fallan si fallan sus pasos.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos. `.github/workflows/ci.yml`
    con los nueve trabajos (`infra`, `backend-quality`, `backend-tests` con cobertura y
    `fail_under`, `contract`, `frontend-quality` con verificación de que `api:generate` no deja
    cambios, `e2e`, `lighthouse`, `build` y `security` con Trivy sobre el repositorio y las dos
    imágenes, CRITICAL/HIGH, `exit-code 1`), `REQUIRE_DOCKER=1` en todo el flujo y permisos de
    solo lectura. `contract`, `e2e` y `lighthouse` tienen un primer paso `enabled` que revisa si
    existe su configuración (T059, T069, fase 11) y omiten sus pasos hasta entonces (`hashFiles`
    no se permite en el `if` de un trabajo; lo detectó actionlint). `.github/dependabot.yml` para
    uv, npm, docker y GitHub Actions. Corregido en la prueba de T007 el indicador de actionlint
    (`-no-color`). T007 completa: 11 de 11 en verde.
- [x] T015 [P] Redactar el borrador de política `backend/seeds/politica_tratamiento_datos_v1.md` (responsable, finalidades, datos recogidos según FR-004 y FR-019/020, derechos de consulta, rectificación, revocación y supresión, plazos de conservación de FR-034a/b, canales de atención), marcado "BORRADOR — pendiente de aprobación de la oficina jurídica" → Opus
  - Estado: borrador redactado por Opus en `backend/seeds/politica_tratamiento_datos_v1.md`; los datos del responsable y los canales quedan como `[PENDIENTE]` hasta que la oficina jurídica los apruebe (riesgo externo de plan.md).
  - Terminado: cumple FR-016 (finalidad, datos, derechos y canales) y supera 200 caracteres (restricción del contrato).
  - Cerrada (2026-10-06): el borrador cumple su criterio; la aprobación de la oficina jurídica
    sigue como riesgo externo de plan.md y se exige antes de publicar la versión 1.0 (US2).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Kernel compartido, esquema de datos, sesión propia, autorización, guardia de
consentimiento, correo y base del frontend. Ninguna historia empieza antes de terminar esta fase.

### Kernel compartido (backend)

- [x] T016 [P] Prueba: configuración por entorno en `backend/tests/unit/shared/test_config.py` (carga de variables de T013, error claro si falta un secreto obligatorio, `INSTITUTIONAL_EMAIL_DOMAINS` como lista, secretos excluidos de `repr`) → Qwen
  - Terminado: la prueba falla porque no existe `config.py`.
  - Nota de Opus (2026-10-06): variables, validaciones y API de `config.py` definidas en
    `handoffs/qwen-02-T016-T017-T022-T023.md`; `ConfigError` nunca incluye el valor recibido.
  - Estado: ver T017.
- [x] T017 Implementar `backend/src/saber_uli/config.py` con pydantic-settings para que pase T016 → Qwen
  - Terminado: T016 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T016 falló por
    `ImportError` (commit `f89a948`). `Settings` con las 22 variables de la tabla del lote 02;
    autoridad de Entra ID obligatoriamente la del inquilino (rechaza `common`, `organizations`,
    `consumers` y otros inquilinos; http solo para `localhost`, `127.0.0.1` y `oidc`); HTTPS
    obligatorio en `PUBLIC_BASE_URL` fuera de localhost; dominios separados por comas
    (`NoDecode`), normalizados y sin duplicados; secretos de 256 bits mínimo; URL de datos como
    `SecretStr`. `get_settings()` lanza `ConfigError` con los nombres de las variables, sin
    valores y sin encadenar el `ValidationError` original (`from None`). 43 pruebas en verde.
- [x] T018 [P] Prueba: procesador de logs sin datos personales en `backend/tests/unit/shared/test_logging.py` (elimina o enmascara las claves `email`, `name`, `correo`, `nombre`, `token`, `authorization`, `cookie`, `code`, `display_name`; enmascara cualquier valor con forma de correo; salida JSON; research R-23) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-06); falló por `ImportError` antes de T019 (commit
    `9084ba0`). Al implementar T019 se agregaron dos cambios: un caso para parámetros sensibles en
    URL (`?code=…&state=…` del callback OIDC aparece en el log de acceso de uvicorn) y la lectura
    de la salida por un `StringIO` inyectado en lugar de `capsys`.
- [x] T019 Implementar `backend/src/saber_uli/shared/infrastructure/logging.py` (structlog JSON + procesador de T018) → Opus
  - Terminado: T018 en verde.
  - Estado: implementada por Opus (2026-10-06). `configure_logging(level, stream)` enruta structlog
    y la librería estándar (incluidos `uvicorn`, `uvicorn.error` y `uvicorn.access`, que se
    redirigen al manejador raíz) por un único `ProcessorFormatter` JSON; `scrub_personal_data` es
    el último procesador antes de renderizar, así que también limpia las excepciones ya
    formateadas. Enmascara las claves de R-23 más variantes compuestas (`user_email`,
    `refresh_token`, `set-cookie`), nombres de persona (`given_name`, `preferred_username`…),
    `state`, `nonce` y `code_verifier`; no toca `status_code` ni `program_name`. T058 debe llamar a
    `configure_logging` al arrancar y lanzar uvicorn con `log_config=None`.
- [x] T020 [P] Prueba: Problem Details y paginación en `backend/tests/unit/shared/test_problems.py` (respuesta `application/problem+json`, `type` = `urn:saber-uli:problem:<slug>`, `errors` por campo en 422, `page`≥1, `page_size` 1–100 por defecto 25, `total`) → Qwen
  - Terminado: la prueba falla.
  - Nota de Opus (2026-10-06): API y reglas de traducción en `handoffs/qwen-03-T020-T021.md`.
    Requiere T023. Incluye `ProblemException` para los problemas de la capa API (T036, T048,
    T052, T058) y `about:blank` para errores HTTP genéricos y 500; las respuestas nunca repiten
    el valor recibido ni el texto de una excepción.
  - Estado: ver T021.
- [x] T021 Implementar `backend/src/saber_uli/shared/api/problems.py` (excepciones de dominio → Problem, manejadores de FastAPI, incluido 422 de validación) y `backend/src/saber_uli/shared/api/pagination.py` → Qwen
  - Terminado: T020 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T020 falló por
    `ImportError` (commit `27b64f6`). `install_problem_handlers` traduce las categorías de
    dominio (404/403/409/422, con `STATUS_BY_SLUG` para excepciones puntuales), `ProblemException`
    (conserva cabeceras como `Retry-After`), validación (422 con `errors` en español construidos
    solo con `loc`, `type` y `ctx`), 404 de ruta como `not-found`, otros errores HTTP como
    `about:blank` y 500 sin detalle (se registra con structlog). `instance` sin la consulta.
    `Page[T]`, `PageParams` y `page_params` según el contrato. 19 pruebas en verde. Aviso:
    Starlette marca como obsoleto su `TestClient` sobre `httpx` (recomienda `httpx2`); no afecta
    hoy y se revisará al actualizar dependencias.
- [x] T022 [P] Prueba: bloques de dominio en `backend/tests/unit/shared/test_domain_base.py` (`DomainEvent` con `event_id` uuid y `occurred_at`; `Clock` del sistema y `FixedClock` para pruebas; errores de dominio con slug) → Qwen
  - Terminado: la prueba falla.
  - Nota de Opus (2026-10-06): API definida en `handoffs/qwen-02-T016-T017-T022-T023.md`;
    errores con categorías `NotFoundError`, `PermissionDeniedError`, `ConflictError` y
    `RuleViolationError` que T021 traduce a 404, 403, 409 y 422.
  - Estado: ver T023.
- [x] T023 Implementar `backend/src/saber_uli/shared/domain/{events.py,clock.py,errors.py}` → Qwen
  - Terminado: T022 en verde; `lint-imports` confirma que `shared.domain` no importa infraestructura.
  - Nota de Opus (2026-10-06): agregar la fixture `fixed_clock` a `backend/tests/conftest.py`.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T022 falló por
    `ImportError` (commit `c22aa50`). `DomainEvent` (dataclass congelada, `event_id` uuid4,
    `occurred_at` obligatorio en UTC, `event_type` validado al definir la subclase),
    `SystemClock`/`FixedClock` (normaliza a UTC, rechaza fechas sin zona) y errores por categoría
    (`NotFoundError`, `PermissionDeniedError`, `ConflictError`, `RuleViolationError`; slug
    kebab-case validado; `DomainError` no instanciable). Fixture `fixed_clock` en
    `backend/tests/conftest.py`. `lint-imports`: 5 KEPT.
- [x] T024 [P] Crear fixtures de pruebas en `backend/tests/conftest.py` y `backend/tests/integration/conftest.py`: contenedores `postgres:18` (con los scripts de `infra/postgres/init/`) y `redis:8`, aplicación de migraciones, sesión por prueba con rollback, `FixedClock`, cliente `httpx.AsyncClient` sobre la app ASGI, fábrica de usuarios por rol y emisor de tokens de prueba → Qwen
  - Terminado: una prueba de humo de integración arranca los contenedores y hace `SELECT 1` con el rol `saber_app`.
  - Nota de Opus (2026-10-06): alcance. T024 entrega contenedores, motores por rol, sesión con
    rollback, cliente de Redis y la fixture que aplica migraciones (usable desde T026). Las demás
    fixtures las agrega la tarea que crea lo que necesitan: `fixed_clock` en T023, fábrica de
    usuarios en T044, emisor de tokens de prueba en T046 y cliente ASGI en T058.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos; la prueba de humo
    falló por falta de fixtures (commit `253179a`). `tests/integration/conftest.py`: `postgres:18`
    con los scripts de `infra/postgres/init/` y contraseñas aleatorias, `redis:8-alpine`,
    `database_urls` por rol (espera a poder entrar como `saber_app`), `app_engine` y
    `migrator_engine` por prueba con `NullPool`, `db_session` con savepoint y rollback final,
    `redis_client` con `flushdb` y `migrated_database` (importa `run_migrations` de T026 solo al
    usarse). Todo `tests/integration/` recibe el marcador `integration` y se omite sin Docker
    salvo con `REQUIRE_DOCKER=1`. Prueba de humo (6) en verde: `saber_app` entra, no crea tablas;
    `saber_migrator` crea esquemas; extensiones presentes; Redis responde. Suite completa: 150
    en verde. Se silencia un aviso de obsolescencia interno de testcontainers 4.13.
- [x] T025 [P] Prueba: unidad de trabajo en `backend/tests/integration/shared/test_unit_of_work.py` (commit persiste; excepción hace rollback; eventos del bus en proceso se despachan solo tras el commit) → Qwen
  - Terminado: la prueba falla.
  - Nota de Opus (2026-10-06): diseño del bus en dos fases (`in_transaction` y `after_commit`,
    precisión en R-08), puerto `UnitOfWork`, `env.py` sin `get_settings()`, CLI con argparse y
    pruebas en `handoffs/qwen-04-T025-T026.md`.
  - Estado: ver T026.
- [x] T026 Implementar `backend/src/saber_uli/shared/infrastructure/db.py` (engine asyncpg, sesiones), `backend/src/saber_uli/shared/application/unit_of_work.py`, `backend/src/saber_uli/shared/application/event_bus.py` y `backend/migrations/env.py` (Alembic asíncrono, varios esquemas, `alembic_version` en `shared`) → Qwen
  - Terminado: T025 en verde; `saber-uli migrate` aplica cero migraciones sin error.
  - Nota de Opus (2026-10-06): T026 crea también `backend/src/saber_uli/cli.py` con el comando
    `migrate` (`alembic upgrade head` con el rol `saber_migrator`); lo usan el servicio `migrate` de
    Compose (T008, T012) y la fixture de migraciones de T024.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T025 falló por
    `ImportError` (commit `9c8a3fb`) y la prueba de la CLI también (commit `19c743b`).
    `EventBus` con fases `in_transaction` y `after_commit` (suscripción por clase base, orden de
    suscripción, fallos de `after_commit` registrados solo con `event_type`, `event_id`,
    manejador y clase de excepción). `UnitOfWork` (puerto: commit explícito, rollback al salir,
    `record` prohibido durante `in_transaction`) y `SqlAlchemyUnitOfWork` con `.session`.
    `db.py` con `create_engine`, `create_session_factory` y `Base` con convención de nombres.
    Alembic: `migrations/env.py` asíncrono (URL desde `attributes["url"]` o
    `MIGRATION_DATABASE_URL`, nunca `get_settings()`; crea `shared` y deja ahí
    `alembic_version`; autogenerado limitado a `shared` e `identity`), `script.py.mako` y
    `alembic.ini` solo para crear revisiones. `run_migrations` y `migrations_dir`
    (`SABER_MIGRATIONS_DIR` o `backend/migrations`). `saber-uli migrate` con argparse: código 2
    sin la variable, 1 ante error (contraseña ocultada), logs JSON. Pruebas: 16 de T025 y 4 de
    la CLI en verde (idempotente; `saber_app` no puede migrar). Verificado en Compose: el
    servicio `migrate` aplica cero migraciones, `shared` es de `saber_migrator` y existe
    `shared.alembic_version`. Suite: 170 en verde; `lint-imports` 5 KEPT.
  - Nota para T028: `env.py` ya crea el esquema `shared`; la migración 0001 debe usar
    `CREATE SCHEMA IF NOT EXISTS shared` o no crearlo. Las revisiones se crean con
    `--rev-id 0001`, `0002`…

### Esquema de datos

- [x] T027 [P] Prueba: restricciones del esquema en `backend/tests/integration/identity/test_schema_constraints.py`, citando data-model.md: `users.kind IN ('institutional','guest')`; `users.status IN ('active','disabled','deletion_pending','deleted')`; `UNIQUE (entra_tenant_id, entra_object_id)`; una lápida (`status='deleted'`) exige `email`, `display_name` y `entra_object_id` en `NULL`; índice único parcial de correo de invitado vigente; `profiles.semester BETWEEN 1 AND 12`; `daily_goal IN ('casual','regular','intense')`; `role IN ('student','guest','teacher','program_director','admin')`; `invitations.status IN ('sent','accepted','expired','revoked')` y una sola invitación `sent|accepted` por correo; `access_links.purpose IN ('invitation','sign_in')` y `token_hash` único; `consents.decision IN ('accepted','rejected','revoked')`; `deletion_requests.origin` y `status` según data-model §2.12 con una sola solicitud abierta por usuario; claves por defecto `uuidv7()` → Qwen
  - Terminado: la prueba falla porque las tablas no existen.
  - Estado: ver T028.
- [x] T028 Implementar las migraciones `backend/migrations/versions/0001_shared_outbox.py` (esquema `shared`, `outbox_events` con índice parcial `(available_at) WHERE processed_at IS NULL`) y `backend/migrations/versions/0002_identity_schema.py` (todas las tablas de data-model.md §2 con sus `CHECK`, FK, índices y extensión `citext`) → Qwen
  - Terminado: T027 en verde; `alembic downgrade base` y `upgrade head` funcionan.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T027 falló al no
    existir las tablas (commit `8f558ab`) y la prueba de ida y vuelta también (commit
    `1170197`). Migraciones en SQL explícito (una sentencia por `op.execute`, como exige
    asyncpg) con nombres de restricciones según la convención de `Base`: 0001 crea
    `shared.outbox_events` (payload solo objeto JSON, `attempts ≥ 0`, índice parcial de
    pendientes) y 0002 las 18 tablas de `identity` con todos los `CHECK`, FK, únicos e índices de
    data-model §2. Agregados por Opus, coherentes con data-model: los invitados no tienen
    identidad de Entra ID; `token_hash` debe medir 32 bytes (SHA-256, R-19);
    `auth_epoch ≥ 0`; `action` de auditoría con formato `contexto.accion`; `details` y `rows`
    con tipo JSON validado; `audit_events` sin FK (la supresión no la toca); `batch_id` con
    `ON DELETE SET NULL` (los lotes se purgan a los 30 días). T027 (27 pruebas, con
    `saber_migrator` porque los permisos de `saber_app` llegan en 0003) en verde;
    `downgrade base` y `upgrade head` en verde. Suite: 198 en verde.
- [x] T029 [P] Prueba: permisos de base de datos en `backend/tests/integration/identity/test_db_grants.py`: con el rol `saber_app`, `UPDATE` y `DELETE` sobre `identity.audit_events` y `identity.consents` fallan, `UPDATE` sobre `identity.policy_versions` falla, `INSERT`/`SELECT` funcionan; `saber_app` no puede ejecutar DDL; `saber_bi` no lee el esquema `identity` (FR-035, research R-07) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T030.
- [x] T030 Implementar `backend/migrations/versions/0003_identity_grants.py` (grants por rol, `ALTER DEFAULT PRIVILEGES`, revocaciones de `UPDATE`/`DELETE` en tablas de solo inserción) → Opus
  - Terminado: T029 en verde.
  - Estado: implementadas por Opus (2026-10-06); T029 falló en lo que depende de los permisos
    (commit `d68abae`). Migración 0003: `saber_app` con DML en `identity` y en
    `shared.outbox_events` (sin DDL, sin `TRUNCATE`, sin acceso de escritura a
    `alembic_version`); `UPDATE` y `DELETE` revocados en `audit_events`, `consents` y
    `policy_versions`; `DELETE` revocado en `users` (la supresión deja lápida, FR-033); privilegios
    por defecto de `saber_migrator` en `identity` y `shared` para tablas futuras. `saber_bi` sin
    acceso a `identity` ni `shared`. Downgrade simétrico. T029 (12 pruebas) en verde; suite: 210.
  - Nota para migraciones futuras: los privilegios por defecto dan DML completo a `saber_app`;
    una tabla nueva de solo inserción debe revocar `UPDATE` y `DELETE` en su propia migración.

### Outbox, worker y límites

- [x] T031 [P] Prueba: outbox en `backend/tests/integration/shared/test_outbox.py` (evento escrito en la misma transacción; rollback no deja evento; despacho con `FOR UPDATE SKIP LOCKED` sin doble entrega con dos despachadores concurrentes; manejador idempotente por `event_id`; reintento con espera y `last_error` sin datos personales; purga a los 7 días de procesado; payload rechazado si contiene claves `email`, `name` o `token`) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T032.
- [x] T032 Implementar `backend/src/saber_uli/shared/infrastructure/outbox.py` (escritor, despachador, registro de manejadores, purga) para que pase T031 → Qwen
  - Terminado: T031 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T031 falló por
    `ImportError` (commit `5d2a808`). `register_outbox(bus, *eventos, context=...)` escribe en la
    fase `in_transaction` con `id = event_id` y `available_at = occurred_at`; el payload son los
    campos del evento salvo `event_id` y `occurred_at`, y claves de nombre, correo, token,
    contraseña, secreto o `code` lanzan `PersonalDataInOutboxError` (la acción se revierte).
    `OutboxDispatcher.dispatch_once` reclama lotes con `FOR UPDATE SKIP LOCKED`, entrega a los
    manejadores de `OutboxRegistry`, marca `processed_at` o reintenta con espera 5 s · 2^(n-1)
    (máx. 1 h) guardando solo la clase de la excepción; un evento sin manejador se marca
    procesado. `purge_processed` borra lo procesado hace más de 7 días. Todas las fechas con el
    reloj inyectado. `OutboxEventRow` registrado en `migrations/env.py`. 10 pruebas en verde.
- [x] T033 [P] Prueba: programación de Celery en `backend/tests/unit/test_worker_schedule.py` (zona `America/Bogota`; `dispatch_outbox` cada 5 s; `expire_invitations` cada hora; `process_retention` diaria 02:00; `process_deletion_requests` cada 15 min; `purge_expired_auth_artifacts` diaria; research R-09) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T034.
- [x] T034 Implementar `backend/src/saber_uli/worker.py` (app Celery, Beat, tarea `dispatch_outbox`; las demás tareas como registros que cada historia completa) → Qwen
  - Terminado: T033 en verde; el servicio `worker` responde a `celery inspect ping`.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T033 falló por
    `ImportError` (commit `38ce691`). `saber_uli/worker.py`: app Celery sobre Redis (zona
    America/Bogota, `acks_late`, `reject_on_worker_lost`, `prefetch=1`, logs JSON vía
    `setup_logging`), las cinco tareas de R-09 programadas (`dispatch_outbox` cada 5 s con
    `expires=5`; `expire_invitations` cada hora; `process_retention` 02:00;
    `process_deletion_requests` cada 15 min; `purge_expired_auth_artifacts` 03:30, que por ahora
    purga el outbox). `dispatch_outbox` usa `OutboxDispatcher`; las demás quedan registradas para
    T126, T156, T157 y US4/US7. `HeartbeatScheduler` toca `/tmp/beat-heartbeat` en cada ciclo
    (Beat arranca con `--scheduler saber_uli.worker:HeartbeatScheduler`). Override de mypy
    acotado a `saber_uli.worker` por falta de tipos de Celery. 9 pruebas de T033 en verde.
    Verificado en Compose: T007 con 10 de 11 pruebas en verde (todos los servicios `healthy`,
    incluidos `worker` y `beat`, y `migrate` con código 0); falta solo `test_flujo_de_ci` (T014).
- [x] T035 [P] Prueba: limitación de peticiones en `backend/tests/integration/shared/test_rate_limit.py` (ventanas de research R-31: 5/h por hash de correo y 20/h por IP en solicitud de enlace; 60/min por IP en consumo de enlace (precisión de R-31 en T120); 30/min por IP en ingreso Microsoft y renovación; 300/min por usuario en el resto; respuesta 429 `rate-limited` con `Retry-After`; la clave por correo usa hash, nunca el correo) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T036.
- [x] T036 Implementar `backend/src/saber_uli/shared/infrastructure/rate_limit.py` y la dependencia FastAPI en `backend/src/saber_uli/shared/api/rate_limit.py` con `limits` + Redis → Opus
  - Terminado: T035 en verde.
  - Estado: implementadas por Opus (2026-10-06); T035 falló por `ImportError` (commit
    `ca9c274`). `RateLimiter` con `limits` 5.8 (`RedisStorage` asíncrono con el cliente
    `redis` ya instalado, `implementation="redispy"`, prefijo `saber-uli:rl`) y ventana
    deslizante con contador. Reglas de R-31 como constantes (`GUEST_LINK_PER_EMAIL`,
    `GUEST_LINK_PER_IP`, `GUEST_SESSION_PER_IP`, `AUTH_PER_IP` compartida por el ingreso con
    Microsoft y la renovación, `API_PER_USER`). Clave por correo: HMAC-SHA256 del correo
    normalizado (el correo no llega a Redis). Dependencias `per_ip`, `per_user` y
    `RateLimitGuard.check_email`; 429 `rate-limited` con `Retry-After` (entre 1 s y la ventana).
    T035 (7 pruebas con Redis real) en verde; suite: 217.
  - Decisión de Opus (revisar en T070): si Redis no responde, la limitación se omite (se permite
    la petición y se registra `rate_limit_unavailable` sin IP ni correo), coherente con R-16, que
    tolera la caída de Redis.
  - Nota para T058: crear `RateLimiter(settings.redis_url, hash_key=...)` en
    `app.state.rate_limiter`, con una clave HMAC derivada (por ejemplo
    `HMAC(SESSION_COOKIE_SECRET, "saber-uli/rate-limit-email")`), nunca el secreto tal cual.
  - Precisión de Opus (2026-10-07, en T081): `AUTH_PER_IP` (30/min compartido) se reemplazó por
    `MICROSOFT_LOGIN_PER_IP` (120/min) y, en la renovación, `REFRESH_PER_SESSION` (30/min por
    HMAC de la cookie) más `REFRESH_PER_IP` (600/min). Motivo: NAT del campus. Ver R-31.

### Correo (contexto notifications)

- [x] T037 [P] Prueba: correo en `backend/tests/unit/notifications/test_templates.py` (plantillas HTML y texto en es-CO, autoescape activo, enlaces absolutos con `PUBLIC_BASE_URL`) y `backend/tests/integration/notifications/test_smtp_sender.py` (envío real a un contenedor Mailpit, verificado por su API) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: ver T038.
- [x] T038 Implementar `backend/src/saber_uli/notifications/application/public.py` (fachada `send_email(template, to, context)`), `backend/src/saber_uli/notifications/application/ports.py` (`EmailSender`), `backend/src/saber_uli/notifications/infrastructure/smtp.py` (smtplib) y `backend/src/saber_uli/notifications/infrastructure/templates/base.{html,txt}.j2` → Qwen
  - Terminado: T037 en verde; los logs del envío no contienen el destinatario.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T037 falló por
    `ImportError` (commit `c5a39a7`). Puertos `TemplateRenderer` y `EmailSender`; fachada
    `EmailService.send_email(template, to, context)` (valida una sola dirección sin saltos de
    línea; registra `email_sent` solo con la plantilla, nunca el destinatario).
    `JinjaTemplateRenderer`: por plantilla `<nombre>.subject.j2`, `.html.j2` (autoescape) y
    `.txt.j2`; `StrictUndefined`; el filtro `absolute_url` solo acepta rutas que empiezan por
    `/` y las une a `PUBLIC_BASE_URL` (ningún enlace a otros dominios); el asunto se limpia de
    saltos de línea. Plantillas `base` (es-CO, pie de la Universidad Libre) y `aviso` (genérica:
    título, párrafos y botón). `SmtpEmailSender` con `smtplib` en un hilo (multipart texto y
    HTML, STARTTLS y autenticación opcionales). T037: 11 pruebas en verde, incluido el envío real
    a un contenedor Mailpit verificado por su API. Las plantillas viajan en la imagen Docker
    (verificado).

### Identidad: usuarios, permisos, sesiones y guardias

- [x] T039 [P] Prueba: matriz de permisos en `backend/tests/unit/identity/test_permissions.py` (permisos de cada rol según research R-22 y el enum `Permission` del contrato; unión de permisos para varios roles (FR-023); `guest` sin permisos de gestión; `teacher` con `invitations:manage_own` y `groups:read_own_students`; `program_director` con `programs:read_aggregated` y sin permisos que expongan datos personales (FR-026); `admin` con todos) → Opus
  - Terminado: la prueba falla.
- [x] T040 Implementar `backend/src/saber_uli/identity/domain/roles.py` y `backend/src/saber_uli/identity/domain/permissions.py` → Opus
  - Terminado: T039 en verde.
  - Estado: implementadas por Opus (2026-10-06); T039 falló por `ModuleNotFoundError` antes de
    T040 (commit `456b3ba`). `Role` y `Permission` son `StrEnum` y una prueba los compara con los
    enums del contrato para detectar desajustes. Matriz: `student` y `guest` sin permisos;
    `teacher` con `invitations:manage_own` y `groups:read_own_students`; `program_director` solo
    con `programs:read_aggregated` (FR-026); `admin` con los 11. `permissions_for` une los
    permisos de varios roles (FR-023) y lanza `ValueError` ante un rol desconocido.
    `has_privileged_role` (docente, director, administrador) queda listo para el claim `priv` de
    T045–T046. R-22 se alineó con el contrato, que tiene además `programs:manage` y
    `deletions:read`. Se agregaron `pyyaml` y `types-pyyaml` como dependencias de desarrollo.
- [x] T041 [P] Prueba: agregado `User` en `backend/tests/unit/identity/test_user.py` (creación institucional con `student`; transiciones `active↔disabled`, `→deletion_pending→deleted` y `deleted` final; cada transición que revoca sesiones incrementa `auth_epoch`; registrar ingreso actualiza `last_login_at` y limpia `retention_notice_sent_at`; `to_tombstone()` deja nombre, correo y `oid` en `None`) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T042.
- [x] T042 Implementar `backend/src/saber_uli/identity/domain/user.py` → Qwen
  - Terminado: T041 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T041 falló por
    `ImportError` (commit `04c68e4`). `User` (dataclass, `id = None` hasta que la base asigna
    `uuidv7()`), `UserKind`, `UserStatus`, `InstitutionalIdentity`. Transiciones de §4.1
    (`disable`, `reactivate`, `request_deletion`, `to_tombstone`; `deleted` final) con
    `InvalidUserTransitionError` (409 `conflict`); `invalidate_sessions()` incrementa
    `auth_epoch` y lo usan desactivar, solicitar supresión y retirar roles; `record_login`
    actualiza correo y nombre del directorio, `last_login_at` y limpia
    `retention_notice_sent_at`; `grant_role`/`revoke_role` con `guest-role-exclusive` y
    `student-role-required` (slugs del contrato). La regla del último administrador queda para
    la aplicación (necesita `FOR UPDATE`). 24 pruebas en verde.
- [x] T043 [P] Prueba: repositorios en `backend/tests/integration/identity/test_user_repository.py` (guardar y leer `User` con roles; buscar por `(tid, oid)`; búsqueda de invitado vigente por correo sin distinguir mayúsculas; bloqueo de administradores activos con `FOR UPDATE`) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T044.
- [x] T044 Implementar `backend/src/saber_uli/identity/infrastructure/orm.py` (mapeos SQLAlchemy de data-model.md) y `backend/src/saber_uli/identity/infrastructure/repositories/users.py` → Qwen
  - Terminado: T043 en verde.
  - Nota de Opus (2026-10-06): agregar la fábrica de usuarios por rol a
    `backend/tests/integration/conftest.py`.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T043 falló por
    `ImportError` (commit `9b71a04`). `identity/infrastructure/orm.py` con las 18 tablas de
    data-model §2 (nombres de PK, FK, únicos e índices idénticos a 0002; los `CHECK` solo en la
    migración). Puerto `UserRepository` en `identity/application/ports.py` y
    `SqlAlchemyUserRepository` (`add` asigna el `uuidv7` de la base; `save` sincroniza roles;
    búsqueda por `(tid, oid)`; invitado vigente por correo sin distinguir mayúsculas;
    `lock_active_admins` con `FOR UPDATE OF users`). La lápida conserva `entra_tenant_id` (no es
    dato personal) y borra `oid`, correo, nombre y roles. Prueba nueva: el ORM coincide con el
    esquema migrado (`compare_metadata`), verificada con una mutación (nullable en `campus` →
    falla). `migrations/env.py` importa el ORM de identity. `app_engine` ahora depende de
    `migrated_database`. Fábrica `user_factory` en `tests/integration/conftest.py`. Suite: 250.
- [x] T045 [P] Prueba: política de sesión y tokens en `backend/tests/unit/identity/test_session_policy.py` (JWT HS256 de 600 s con `kid` y claims `sub`, `sid`, `roles`, `epoch`, `priv`, `iat`, `exp`; token de renovación de 256 bits guardado solo como SHA-256; rotación en cada uso; reutilizar un token rotado revoca la sesión; inactividad 7 días y absoluto 30 días; `priv=true` solo con rol privilegiado, `auth_time` < 12 h y actividad privilegiada < 30 min; una sesión recién creada o reautenticada inicializa `last_privileged_activity_at = auth_time`, así que un administrador recién autenticado obtiene `priv=true`; con 31 min sin actividad privilegiada obtiene `priv=false`; research R-14 y R-15) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T046.
- [x] T046 Implementar `backend/src/saber_uli/identity/domain/session.py`, `backend/src/saber_uli/identity/infrastructure/tokens.py` y `backend/src/saber_uli/identity/infrastructure/repositories/sessions.py` → Opus
  - Terminado: T045 en verde.
  - Nota de Opus (2026-10-06): agregar el emisor de tokens de prueba a
    `backend/tests/integration/conftest.py`.
  - Estado: implementadas por Opus (2026-10-06); T045 falló por `ImportError` (commit
    `e935fd3`) y la prueba del repositorio también (commit `c94818d`). Dominio: `Session`
    (`start` inicializa la actividad privilegiada con `auth_time`; `is_privileged` exige rol
    privilegiado, autenticación < 12 h y actividad privilegiada < 30 min; `reauthenticate`,
    `revoke`), `RefreshToken.issue` (inactividad de 7 días acotada al límite absoluto de 30) y
    `rotate_refresh_token` (rotación en cada uso; reutilizar un token rotado revoca la sesión con
    `token_reuse` → `session-revoked`; vencida → `session-expired`). Nueva categoría compartida
    `UnauthenticatedError` (401) en `shared.domain.errors` y en `problems.py`, con sus pruebas.
    Infraestructura: `AccessTokenCodec` (HS256 únicamente, `kid` con varias claves para rotar,
    claims exactos, vencimiento con el reloj inyectado, claves de 256 bits como mínimo) y tokens
    de renovación de 256 bits guardados solo como SHA-256. `SqlAlchemySessionRepository` con
    `get_refresh_token_for_update` (`FOR UPDATE`: dos renovaciones simultáneas no rotan el mismo
    token) y `revoke_all_for_user`. Fixtures `token_codec` e `issue_token` en
    `tests/integration/conftest.py`. Suite: 280 en verde.
- [x] T047 [P] Prueba: dependencia de autenticación en `backend/tests/integration/identity/test_auth_dependency.py` (sin token → 401 `unauthenticated`; `epoch` distinto → 401 con causa `account-disabled`, `guest-access-expired`, `guest-access-revoked` o `session-revoked`; ruta `x-requires-privileged-session` sin `priv` → 401 `reauthentication-required`; `auth_epoch` leído de Redis con respaldo en base de datos si Redis falla; la actividad privilegiada actualiza `last_privileged_activity_at`; research R-16) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T048.
- [x] T048 Implementar `backend/src/saber_uli/shared/api/auth.py` (dependencias `current_user` y `require_privileged`), `backend/src/saber_uli/identity/application/access_guard.py` y `backend/src/saber_uli/identity/infrastructure/epoch_cache.py` → Opus
  - Terminado: T047 en verde.
  - Estado: implementadas por Opus (2026-10-06); T047 falló por `ImportError` (commit
    `67c0fdc`). La fachada `identity.application.public` expone `AuthenticatedUser` y el puerto
    `Authenticator` (el kernel solo importa la fachada, contrato `kernel-compartido`).
    `AccessGuard` (aplicación) decodifica el token, compara la época con la caché y, si falta o
    Redis falla, con la base de datos; si no coincide responde la causa: `account-deleted`
    (también en supresión), `account-disabled`, `guest-access-revoked`, `guest-access-expired` o
    `session-revoked`. `RedisEpochStore` (clave `saber-uli:auth-epoch:<id>`, vence a los 5 min,
    errores de Redis registrados sin identificadores). `SqlAlchemyIdentityUnitOfWork` con
    `users`, `sessions` y `guest_access`; `SqlAlchemyGuestAccessReader` deriva el acceso de la
    invitación más reciente. `shared/api/auth.py`: `current_user` (401 `unauthenticated` con
    `WWW-Authenticate: Bearer`) y `require_privileged` (401 `reauthentication-required`; registra
    la actividad privilegiada). `AccessTokenClaims` pasó a los puertos de la aplicación
    (`tokens.py` lo reexporta). T047 (15 pruebas con Postgres y Redis reales) en verde; suite: 295.
  - Nota para T058: armar `AccessGuard` con `AccessTokenCodec`, `RedisEpochStore` y
    `SqlAlchemyIdentityUnitOfWork`, y suscribir en fase `after_commit` un manejador de
    `identity.UserAccessChanged` que llame a `epochs.invalidate(user_id)` (la caché vence a los
    5 minutos si una invalidación se pierde).
  - Decisión de Opus (revisar en T070): el vencimiento natural del acceso de invitado no cambia
    la época por sí solo; lo hará `expire_invitations` (T126) y la renovación (T050) lo comprueba.
    Un token de acceso de un invitado vencido puede durar como máximo sus 10 minutos.
- [x] T049 [P] Prueba: renovación y cierre de sesión en `backend/tests/integration/identity/test_refresh_logout.py` (`POST /api/auth/refresh` exige `X-Requested-With: saber-uli`; cookie `su_refresh` con `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/auth`; rota la cookie; reutilización → 401 `session-revoked` y familia revocada; cuenta desactivada → 401 `account-disabled`; inactividad > 7 días → 401 `session-expired`; `POST /api/auth/logout` → 204 y cookie borrada; escenario 1.4) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T050.
- [x] T050 Implementar `backend/src/saber_uli/identity/application/sessions.py` y `backend/src/saber_uli/identity/api/auth_router.py` (refresh y logout) → Opus
  - Terminado: T049 en verde.
  - Estado: implementadas por Opus (2026-10-06); T049 falló por `ImportError` (commit
    `eea4cbe`). `SessionService` (`open_session` para T076/T107, `refresh`, `logout`): la
    renovación bloquea el token (`FOR UPDATE`), valida cuenta y acceso de invitado (mismas causas
    que T048), rota el token, confirma la revocación por reutilización aunque la petición falle,
    registra el ingreso (conservación, FR-034b/c) y emite `priv` según R-15. Puertos
    `AccessTokenEncoder` y `RefreshTokenGenerator` (`RefreshTokenFactory`). Router con
    `refreshSession` (límite 30/min por IP compartido con el ingreso; cookie `su_refresh` con
    `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/auth` y `Max-Age` hasta el vencimiento
    por inactividad; `Cache-Control: no-store`; ante un 401 la cookie se borra) y `logout` (204,
    revoca la sesión y borra la cookie). T049 (10 pruebas) en verde; suite: 305.
  - Decisión resuelta por Opus en T059 (2026-10-06): refresh y logout exigen la cabecera
    `X-Requested-With: saber-uli` y la cookie (`refreshCookie`); si falta alguna responden 401
    `unauthenticated` y borran la cookie. Schemathesis señaló que logout aceptaba peticiones sin
    la cookie y que su 401 no estaba documentado: el contrato ahora documenta el 401 de logout
    (cambio mínimo) y el cliente del frontend se regeneró.
  - Resuelto en T054: la revocación por reutilización se audita como `session.reuse_detected`.
- [x] T051 [P] Prueba: estado de autorización y guardia de consentimiento en `backend/tests/unit/identity/test_consent_status.py` (vigente solo si el último registro es `accepted` y su versión es la vigente; sin registros, `rejected`, `revoked` o versión anterior → `consent_required`) y `backend/tests/integration/identity/test_consent_guard.py` (ruta sin `x-consent-exempt` → 403 `consent-required`; rutas exentas responden; FR-014) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: ver T052.
- [x] T052 Implementar `backend/src/saber_uli/identity/domain/consent.py` (estado vigente), `backend/src/saber_uli/identity/application/queries/consent_status.py` y `backend/src/saber_uli/shared/api/consent_guard.py` (lista de rutas exentas tomada del contrato) → Qwen
  - Terminado: T051 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T051 falló por
    `ImportError` (commit `d5a2163`). `consent_is_current` (último registro `accepted` de la
    versión vigente; sin política publicada no hay autorización posible). `SqlAlchemyConsentReader`
    (último registro; versión vigente = mayor `effective_from ≤ now`) dentro de la unidad de
    trabajo. `ConsentStatusQuery` implementa el puerto `ConsentChecker` de la fachada pública y
    da `status()` para `/me` (T079). `require_consent` omite las operaciones públicas
    (`getCurrentPolicy`, `getPolicyVersion`, sin sesión) y las `x-consent-exempt` (con sesión);
    el resto sin autorización vigente → 403 `consent-required`, siempre después del 401. Las dos
    listas copian el contrato y una prueba verifica que coincidan. Fixture `committed_login` en
    el conftest de integración. 15 pruebas en verde.
  - Nota: mientras no se publique una versión de la política (US2), toda ruta no exenta de
    `/api/v1` responde 403 `consent-required`.
- [x] T053 [P] Prueba: auditoría en `backend/tests/integration/identity/test_audit_writer.py` (el evento se escribe en la misma transacción que la acción; `action` del catálogo de data-model §5; rechaza `details` con claves `email`, `name`, `display_name` o valores con forma de correo; `actor_id` `NULL` = sistema) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T054.
- [x] T054 Implementar `backend/src/saber_uli/identity/application/audit.py` y `backend/src/saber_uli/identity/infrastructure/repositories/audit.py` → Qwen
  - Terminado: T053 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T053 falló por
    `ImportError` (commit `fbc368d`). `AuditAction` (catálogo cerrado de data-model §5; una
    prueba lo compara con el documento), `AuditTarget`, `AuditEntry` y `record_audit`, que
    escribe con la misma unidad de trabajo que la acción (`uow.audit`) y rechaza antes de escribir
    claves de nombre o correo (también anidadas y sin distinguir mayúsculas) y cualquier valor con
    forma de correo (`PersonalDataInAuditError`). `SqlAlchemyAuditRepository` solo inserta.
    Cerrado el pendiente de T050: la renovación audita `session.reuse_detected` una sola vez al
    revocar por reutilización. T053 (11 pruebas) en verde; suite: 331.
- [x] T055 [P] Prueba: parámetros en `backend/tests/unit/identity/test_settings.py` (valores por defecto `teacher_max_access_days`=180, `default_guest_access_days`=90, `invitation_link_ttl_days`=7, `sign_in_link_ttl_minutes`=15; rangos del contrato: 1–730, 1–730, 1–30, 5–60) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T056.
- [x] T056 Implementar `backend/src/saber_uli/identity/domain/settings.py` y `backend/src/saber_uli/identity/infrastructure/repositories/settings.py` (con semilla de valores por defecto en la migración `backend/migrations/versions/0004_identity_settings_seed.py`) → Qwen
  - Terminado: T055 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T055 falló por
    `ImportError` (commit `78a05a2`). `IdentitySettings` (dataclass inmutable con los valores
    por defecto; valida los rangos del contrato y lanza `SettingOutOfRangeError`, 422;
    `with_changes`, `changed_keys` y duraciones como `timedelta`). Migración 0004 siembra los
    cuatro valores con `ON CONFLICT DO NOTHING` (no pisa cambios de un administrador).
    `SqlAlchemySettingsRepository.load` toma el valor por defecto si falta una clave y `save`
    solo escribe las claves cambiadas, con `updated_by`. Suite: 343 en verde.
- [x] T057 [P] Prueba: arranque de la API en `backend/tests/integration/test_health.py` (`GET /api/health` → `{"status":"ok"}`; `GET /api/ready` → 503 si la base de datos o Redis no responden; logs JSON en cada petición sin datos personales) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T058.
- [x] T058 Implementar `backend/src/saber_uli/main.py` (app FastAPI, routers, manejadores de problemas, logging, `SessionMiddleware` acotada a `/api/auth/microsoft`) y `backend/src/saber_uli/shared/api/health.py` → Qwen
  - Terminado: T057 en verde; `docker compose up` deja `api` en `healthy`.
  - Nota de Opus (2026-10-06): agregar el cliente `httpx.AsyncClient` sobre la app ASGI a
    `backend/tests/integration/conftest.py`. Al cerrar T058, T007 debe pasar completa (servicios
    `api`, `worker`, `beat` y `migrate` incluidos; ver la nota de T012).
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T057 falló por
    `ImportError` (commit `5d18587`). `main.create_app(settings, clock, log_stream)` es la raíz de
    composición: logs JSON, motor y sesiones de `saber_app`, bus de eventos (invalida la caché de
    épocas tras el commit de `identity.UserAccessChanged`, evento nuevo en
    `identity/domain/events.py`), `AccessTokenCodec`, `RateLimiter` con clave HMAC derivada del
    secreto de sesión, `AccessGuard`, `ConsentStatusQuery`, `SessionService`, manejadores de
    Problem Details y routers de salud y de sesión. `SessionMiddleware` solo bajo
    `/api/auth/microsoft` (`PathScopedMiddleware`, cookie `su_oidc` de 10 min con clave derivada).
    `RequestLoggingMiddleware`: un log `http_request` por petición (método, ruta sin consulta,
    estado, duración, `request_id` también en `X-Request-ID`). `GET /api/health` y
    `GET /api/ready` (base de datos y Redis con 2 s cada uno; 503 `service-unavailable`). Sin
    `/docs` ni `/openapi.json`: el contrato publicado es el de `specs/`. La imagen arranca con
    `uvicorn --factory saber_uli.main:create_app`. Fixtures `settings_for` y `api_client`.
    T057 (8 pruebas) en verde; suite: 351. Verificado en Compose: `migrate` aplica 0001–0004,
    `api` queda `healthy` con UID 10001 y responde por el proxy `/api/health`, `/api/ready` y
    404 como Problem Details.
  - Resuelto: con T034 y T014, T007 pasa completa (11 de 11).
- [x] T059 Crear el arnés de contrato `backend/tests/contract/test_openapi_contract.py` con Schemathesis sobre la app ASGI, autenticado con tokens de prueba por rol, y la lista `backend/tests/contract/implemented_operations.py` (cada historia agrega sus `operationId`) → Qwen
  - Terminado: corre en verde con las operaciones de la fase 2 (`getHealth`, `getReadiness`, `refreshSession`, `logout`).
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos. Schemathesis 4 carga
    el contrato desde `specs/` (la app no publica su esquema), se apunta a la app ASGI completa
    (`create_app` con Postgres y Redis reales) y se filtra con
    `from_fixture(...).include(operation_id=...)` por `implemented_operations.py`. Las rutas con
    `bearerAuth` usan el token de un administrador con sesión privilegiada (`committed_login`).
    `tests/contract/conftest.py` reutiliza las fixtures de integración. En verde con `getHealth`,
    `getReadiness`, `refreshSession` y `logout`. Hallazgos: logout aceptaba peticiones sin la
    cookie y su 401 no estaba en el contrato (resuelto, ver T050). Además, `configure_logging`
    ya no cachea los loggers (`cache_logger_on_first_use=False`): con caché, `capture_logs`
    dejaba de funcionar según el orden de las pruebas. Suite: 383 en verde. El trabajo
    `contract` de CI queda activo.

### Base del frontend

- [x] T060 [P] Prueba: shell de la app en `frontend/src/app/App.test.tsx` (renderiza en es-CO, idioma `lang="es-CO"`, indicador de estado de conexión visible, navegación accesible por teclado) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T061.
- [x] T061 Implementar `frontend/src/app/{main.tsx,router.tsx,providers.tsx,AppShell.tsx}`, `frontend/src/shared/i18n/{index.ts,es-CO.json}` y la base de Tailwind/shadcn en `frontend/src/shared/ui/` → Qwen
  - Terminado: T060 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T060 falló al no
    existir el router (commit `59dfda8`). `App` (acepta un router para pruebas), `Providers`
    (i18next y TanStack Query), `createAppRouter` (TanStack Router en código: `/` redirige a
    `/inicio`, `/inicio` marcador hasta la spec 003, página "no encontrada" en español; historial
    en memoria para pruebas), `AppShell` (enlace "Saltar al contenido" como primer foco que lleva
    el foco a `<main id="contenido">`, navegación "Principal", indicador de conexión con
    `role="status"` y `aria-live` que reacciona a `online`/`offline`), `initI18n` con
    `es-CO.json` y `lang="es-CO"`. `main.tsx` pasó a `src/app/` (`index.html` actualizado). Se
    agregó `@testing-library/jest-dom` con `tests/setup.ts`. Frontend: 58 pruebas, `lint`,
    `typecheck`, `format` y `build` en verde. La base de shadcn/ui ya estaba (T004).
- [x] T062 [P] Prueba: sesión en memoria y cliente HTTP en `frontend/src/features/auth/session.test.ts` con MSW (el token de acceso vive solo en memoria y nunca en `localStorage`/`sessionStorage`/IndexedDB; cabecera `Authorization`; ante 401 intenta una sola renovación con `X-Requested-With: saber-uli` y reintenta; cada `type` de problema se traduce a un mensaje en español) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-06); falló al no existir los módulos (commit
    `8ad0ead`). El catálogo de mensajes se verifica contra el contrato: la prueba lee
    `openapi.yaml?raw` y exige un mensaje propio para cada `type` (27 con guiones más
    `unauthenticated`, `forbidden` y `conflict`); para eso `vite.config.ts` permite leer solo
    `specs/001-identidad-acceso/contracts` (`server.fs.allow`).
- [x] T063 Implementar `frontend/src/shared/api/http.ts` (mutador de orval), `frontend/src/features/auth/session-store.ts` (Zustand sin persistencia) y `frontend/src/shared/api/problem-messages.ts` → Opus
  - Terminado: T062 en verde.
  - Estado: implementada por Opus (2026-10-06). `useSessionStore` (Zustand sin `persist`) guarda
    el token y su vencimiento solo en memoria. `customInstance` agrega `Authorization` y
    `X-Requested-With: saber-uli` a toda petición, usa `credentials: same-origin` y ante un 401
    renueva una sola vez (renovación compartida entre peticiones concurrentes) y reintenta. No
    renueva en rutas `/api/auth/` ni ante `reauthentication-required` (R-15: la UI debe mandar a
    reautenticar). Si la renovación da 401, borra la sesión y lanza la causa (`account-disabled`,
    `guest-access-expired`…); si falla por red, 429 o 5xx conserva la sesión (modo sin conexión,
    FR-038). Los errores son `ApiProblem` (`status`, `type`, `slug`, `errors`, `message` en
    español); sin respuesta del servidor el slug es `network-error` (estado 0) y un 5xx sin
    cuerpo RFC 9457 es `service-unavailable`. Se exporta `refreshAccessToken()` para el arranque
    de T080. Nota: `shared/api/http.ts` importa `features/auth/session-store.ts` porque así lo
    fija la tarea; si se agrega una regla de capas en eslint, mover el store a `shared/`.
- [x] T064 [P] Prueba: acceso sin conexión en `frontend/src/features/auth/offline-access.test.ts` (guarda la instantánea de `/api/v1/me` y `lastValidatedAt` en Dexie; sin red permite usar la app si `ahora − lastValidatedAt ≤ 7 días`; después bloquea con mensaje; al reconectar llama primero a `/api/auth/refresh` y luego a `/api/v1/me` antes de permitir sincronizar; FR-038, FR-039) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T065.
- [x] T065 Implementar `frontend/src/shared/db/dexie.ts` y `frontend/src/features/auth/offline-access.ts` (incluye el hook `useCanSync` que la spec 003 usará) → Qwen
  - Terminado: T064 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T064 falló al no
    existir los módulos (commit `011993c`). `shared/db/dexie.ts` (base `saber-uli`, tabla `meta`;
    nunca guarda tokens). `features/auth/offline-access.ts`: `saveValidation` (instantánea de
    `/me` y `lastValidatedAt`), `evaluateOfflineAccess` (`allowed` hasta 7 días inclusive,
    `expired` con mensaje en español, `none` sin instantánea), `revalidate` (renovación y luego
    `/me` con el token nuevo; la instantánea solo se actualiza si ambas funcionan) y `useCanSync`
    (falso hasta revalidar; se apaga sin conexión y al reconectar vuelve a revalidar). Dependencia
    de desarrollo `fake-indexeddb`. 11 pruebas en verde; frontend: 69.
- [x] T066 [P] Prueba: guardias de navegación en `frontend/src/app/guards.test.tsx` (sin sesión → `/ingresar`; `consent_required` → `/bienvenida/datos`; `profile_required` → `/bienvenida/perfil`; rutas de administración y docente según `permissions`; retomar el paso pendiente del primer ingreso, FR-022) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T067.
- [x] T067 Implementar `frontend/src/app/guards.ts` y su conexión en `frontend/src/app/router.tsx` → Qwen
  - Terminado: T066 en verde.
  - Estado: implementadas por Opus (2026-10-06) porque Qwen no tenía créditos; T066 falló al no
    existir el módulo (commit `4facb22`). `decideNavigation` (función pura): sin sesión →
    `/ingresar?return_to=…` (públicas: `/ingresar`, `/acceso`); autorización pendiente →
    `/bienvenida/datos`; perfil pendiente → `/bienvenida/perfil`; pasos ya completados o
    `/ingresar` con sesión → `/inicio` (FR-022); rutas de docente y administración según
    `permissions` (sin permiso → `/inicio`); más de 7 días sin conexión → `/sin-conexion`
    (FR-039). La ruta raíz del router la aplica en `beforeLoad` con `getSession` del contexto;
    por defecto `createSessionLoader()` (renovación + `/me` con caché; sin red usa la instantánea
    de Dexie o bloquea; T080 llamará a `invalidate()` al ingresar y al salir). Páginas mínimas de
    `/ingresar`, `/acceso`, `/bienvenida/datos`, `/bienvenida/perfil` (las completan T080, T085,
    T097) y `/sin-conexion`. Frontend: 95 pruebas, `lint`, `typecheck` y `build` en verde.
- [x] T068 [P] Configurar la PWA en `frontend/vite.config.ts` (vite-plugin-pwa: manifest con nombre "Saber Uli", `lang: es-CO`, íconos 192/512 y maskable en `frontend/public/icons/`, `display: standalone`, precache del shell) y la guía de instalación para iPhone en `frontend/src/shared/ui/InstallHint.tsx` con su prueba `frontend/src/shared/ui/InstallHint.test.tsx` → Qwen
  - Terminado: `npm run build` genera `sw.js` y `manifest.webmanifest`; la prueba del componente pasa.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos; la prueba del
    componente falló primero (commit `b97e15f`). `vite-plugin-pwa` 2 con `generateSW`: manifiesto
    "Saber Uli" (`lang: es-CO`, `display: standalone`, `start_url: /inicio`, color
    `#15803d`, íconos 192/512 y `maskable`), precache del shell, `navigateFallback` a
    `index.html` sin `/api/` y registro con `injectRegister: "script"` (`/registerSW.js`
    externo: la CSP no permite scripts en línea). `InstallHint` en el shell: solo en iPhone/iPad
    sin instalar, explica "Compartir → Agregar a inicio", se puede cerrar y lo recuerda (tolera
    almacenamiento bloqueado). `tests/setup.ts` inicializa i18n para que las pruebas usen los
    textos reales. Íconos provisionales generados por script (verde con círculo blanco):
    reemplazarlos por el diseño institucional. Verificado: `npm run build` genera `sw.js` y
    `manifest.webmanifest`, y la imagen del proxy los sirve con `Service-Worker-Allowed: /` y
    `no-cache`. Frontend: 100 pruebas en verde.
- [x] T069 [P] Configurar Playwright en `frontend/playwright.config.ts` (viewport móvil Pixel 7 e iPhone 14, `locale: es-CO`) y los fixtures `frontend/tests/e2e/fixtures/{auth.ts,mailpit.ts,axe.ts,api.ts}` (ingreso con el proveedor de prueba eligiendo usuario del inquilino o externo; lectura de correos de Mailpit; chequeo axe nivel AA; llamadas API como administrador) → Qwen
  - Terminado: una prueba de humo abre `/` contra el stack con perfil `e2e`.
  - Estado: implementada por Opus (2026-10-06) porque Qwen no tenía créditos.
    `playwright.config.ts` (proyectos `pixel-7` con Chromium e `iphone-14` con WebKit,
    `locale: es-CO`, zona America/Bogota, trazas al fallar). Fixtures: `axe.ts`
    (`expectNoA11yViolations`, WCAG 2.0/2.1/2.2 A y AA), `mailpit.ts` (búsqueda del último correo
    por destinatario y extracción del enlace), `auth.ts` (formulario interactivo del simulador:
    usuario como `oid` y claims opcionales; `external` envía el `tid` del inquilino externo) y
    `api.ts` (token desde la cookie de la página y contexto HTTP autenticado). Prueba de humo
    (`tests/e2e/smoke.spec.ts`): sin sesión `/` lleva a `/ingresar` en es-CO, sin infracciones
    de axe, con el indicador de conexión; manifiesto en es-CO; `/api/health` por el proxy. Contra
    el stack real con perfil `e2e`: 6 de 6 en verde (3 pruebas × 2 dispositivos). `auth.ts` se
    ejercita desde US1 (T081), cuando existan las rutas de ingreso con Microsoft.
  - Decisión de T012 resuelta: el navegador y la API usan el mismo emisor `http://oidc:8080`; el
    override publica el simulador en `127.0.0.1:8080:8080` y el host agrega `127.0.0.1 oidc` a su
    archivo hosts (CI lo hace en el trabajo `e2e`, que además fija el inquilino de prueba).
    Documentarlo en el quickstart (T177).
- [x] T070 Revisión de seguridad de la fase 2 (T010, T011, T029–T030, T035–T036, T045–T050, T062–T063) en `specs/001-identidad-acceso/tasks.md`: ASVS 4.0.3 V2, V3, V4 y V7 aplicables; secretos solo por entorno; ningún dato personal en logs ni outbox → Opus
  - Terminado: hallazgos corregidos o registrados como tareas nuevas; casillas de la fase 2 marcadas.
  - Revisión de Opus (2026-10-06). Alcance: T010, T011, T029–T030, T035–T036, T045–T050, T062–T063,
    más lo que la fase 2 agregó después (outbox, correo, `main.py`, CI). Comprobado con las pruebas
    automáticas (388 backend, 100 frontend, 11 de infraestructura, contrato con Schemathesis) y en
    Compose.
    - V2 (autenticación): los flujos de ingreso llegan con US1 y US4; lo de la fase 2 cumple:
      límites de R-31 en Redis con clave HMAC del correo (nunca el correo) y 429 con
      `Retry-After`.
    - V3 (sesiones): token de acceso HS256 de 10 min con `kid` y claves ≥ 256 bits; renovación de
      256 bits guardada solo como SHA-256, rotación en cada uso con bloqueo de fila y revocación
      de la sesión ante reutilización (auditada); cookie `HttpOnly`, `Secure`, `SameSite=Strict`,
      `Path=/api/auth`; inactividad 7 días y absoluto 30 días con la desviación de ASVS 3.3.2
      acotada por la sesión privilegiada (12 h / 30 min, R-15); `X-Requested-With` y la cookie
      exigidos en refresh y logout; el token de acceso solo en memoria en el frontend.
      **Corregido**: al cerrar sesión o revocarla por reutilización, el token de acceso ya
      emitido seguía sirviendo hasta 10 min (V3.3.1). Ahora el `sid` entra en una lista de
      sesiones revocadas en Redis (`RedisSessionRevocations`, vence con el token) que
      `AccessGuard` consulta en cada petición.
    - V4 (control de acceso): la API niega por defecto (sin token → 401; sin autorización de
      datos → 403 `consent-required`; rutas privilegiadas sin `priv` → 401
      `reauthentication-required`); matriz de permisos del contrato; permisos de base de datos
      con mínimo privilegio (auditoría y consentimientos de solo inserción, políticas inmutables,
      sin `DELETE` de usuarios, `saber_bi` sin acceso; T029). **Corregido**: faltaba una
      dependencia para exigir permisos por ruta; se agregó `require_permission(...)` (403
      `forbidden`) y `AuthenticatedUser.permissions`.
    - V7 (logs): JSON con limpieza final de claves y valores sensibles (incluidos parámetros de
      URL y excepciones formateadas), log por petición sin consulta ni IP, auditoría y outbox que
      rechazan datos personales, `last_error` solo con la clase, `ConfigError` sin valores,
      Problem Details sin valores recibidos. **Corregido**: el log de acceso de uvicorn (IP y
      consulta) reaparecía porque `configure_logging` lo reconectaba aunque uvicorn arrancara con
      `--no-access-log`; ahora `uvicorn.access` queda silenciado (prueba nueva en T018) y la
      imagen arranca con `--no-access-log`. Verificado en Compose: 0 líneas de `uvicorn.access`.
    - Secretos: solo por entorno (`${VAR:?}` en Compose, `.env` ignorado, detect-secrets en
      pre-commit, Trivy en CI); `migrate` recibe solo su URL; claves HMAC derivadas, nunca el
      secreto tal cual.
    - Riesgos aceptados (documentados): si Redis no responde, la limitación de peticiones, la
      caché de épocas y la lista de sesiones revocadas se omiten (la época se lee de la base); el
      vencimiento natural del acceso de invitado puede tardar hasta 10 min en surtir efecto en un
      token de acceso ya emitido (lo resuelven la renovación y T126).
    - Hallazgos abiertos (tareas nuevas T070a y T070b).
- [ ] T070a [P] Redis con contraseña en producción: `requirepass` en `compose.prod.yaml` y `REDIS_URL` con credenciales armada por Compose desde una variable nueva `REDIS_PASSWORD` (documentada en `.env.example`); prueba en T007 de que `redis-cli ping` sin contraseña falla con el archivo de producción → Qwen
  - Terminado: T007 en verde con la comprobación nueva.
- [ ] T070b [P] Alertas operativas: documentar en quickstart.md (operación) que los eventos `rate_limit_unavailable`, `epoch_cache_unavailable`, `session_revocation_unavailable`, `outbox_delivery_failed` y `readiness_check_failed` deben generar alerta, con un ejemplo de consulta sobre los logs JSON → Qwen
  - Terminado: sección nueva en quickstart.md revisada por Opus.

**Checkpoint**: base lista; las historias pueden empezar (en paralelo si hay capacidad).

---

## Phase 3: User Story 1 - Ingreso con la cuenta institucional (Priority: P1) 🎯 MVP

**Goal**: un miembro de Unilibre entra con Microsoft 365, se crea su cuenta con rol Estudiante y
llega al paso de autorización; cualquier otra cuenta Microsoft es rechazada con un mensaje claro.

**Independent Test**: con el proveedor de prueba, ingresar con un usuario del inquilino (cuenta
creada, redirige a `/bienvenida/datos`) y con uno externo (rechazo, sin cuenta); cerrar sesión.

### Tests for User Story 1 ⚠️

- [x] T071 [P] [US1] Prueba: caso de uso en `backend/tests/unit/identity/test_authenticate_institutional_user.py` (primer ingreso crea usuario `institutional` con rol `student`, nombre y correo de los claims (FR-003); ingreso posterior reutiliza la cuenta por `(tid, oid)` y actualiza nombre y correo (FR-005, escenario 1.3); `tid` distinto → error `tenant_not_allowed` sin crear cuenta (FR-002); cuenta `disabled` → `account-disabled`; registra `last_login_at`; audita `user.created` solo en el primer ingreso) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T076.
- [x] T072 [P] [US1] Prueba: adaptador Entra ID en `backend/tests/integration/identity/test_entra_adapter.py` con respx y JWK generadas (descubrimiento por `.well-known`; PKCE S256; `state` y `nonce` en cookie firmada de 10 min; rechaza firma inválida, `aud` distinto, `nonce` distinto, `iss` de otro inquilino y `tid` distinto; usa la autoridad del inquilino, nunca `common`; toma solo `oid`, `tid`, `name`, `email` o `preferred_username`; research R-10 a R-13) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T077.
- [x] T073 [P] [US1] Prueba: flujo HTTP en `backend/tests/integration/identity/test_microsoft_login_flow.py` (`GET /api/auth/microsoft/login` → 302 a la autoridad del inquilino; `return_to` solo rutas relativas; callback válido → 302 a `/bienvenida/datos` y cookie `su_refresh`; inquilino externo → 302 a `/ingresar?error=tenant_not_allowed` sin crear usuario y log `auth.login_rejected` sin correo (FR-036); proveedor caído → `/ingresar?error=idp_unavailable`; rate limit 30/min por IP) → Opus
  - Terminado: la prueba falla.
  - Estado: ver T078.
- [x] T074 [P] [US1] Prueba: `GET /api/v1/me` en `backend/tests/integration/identity/test_me.py` (campos del esquema `Me`; `permissions` según roles; `onboarding.consent_required` y `profile_required`; `access.offline_grace_until` = `validated_at` + 7 días; responde sin autorización de datos por ser exenta) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T079.
- [x] T075 [P] [US1] Prueba de componente `frontend/src/features/auth/LoginPage.test.tsx` (botón "Ingresar con mi cuenta Unilibre"; mensaje para `tenant_not_allowed` con la alternativa de pedir invitación (SC-008); mensaje para `idp_unavailable`; enlace a ingreso de invitados) → Qwen
  - Terminado: la prueba falla.
  - Estado: ver T080.

### Implementation for User Story 1

- [x] T076 [US1] Implementar `backend/src/saber_uli/identity/application/authenticate_institutional_user.py` para que pase T071 → Qwen
  - Terminado: T071 en verde.
  - Estado: implementadas por Opus (2026-10-07) porque Qwen no tenía créditos; T071 falló por
    `ImportError` (commit `f29ef09`). `AuthenticateInstitutionalUser`: otro `tid` →
    `TenantNotAllowedError` (código `tenant_not_allowed` para `/ingresar?error=`) sin crear cuenta;
    cuenta por (`tid`, `oid`): primer ingreso crea institucional con Estudiante y audita
    `user.created` (sin datos personales, actor sistema); ingresos posteriores actualizan nombre y
    correo y registran `last_login_at`; desactivada → `account-disabled`; en supresión →
    `account-deleted`; sin nombre usa el correo. Dobles en memoria reutilizables en
    `tests/unit/identity/fakes.py`. 6 pruebas en verde.
- [x] T077 [US1] Implementar `backend/src/saber_uli/identity/infrastructure/entra_id.py` (cliente Authlib) para que pase T072 → Opus
  - Terminado: T072 en verde.
  - Estado: implementadas por Opus (2026-10-07); T072 falló por `ImportError` (commit `7711c42`).
    `EntraIdClient`: solo autoridad del inquilino (rechaza `common`, `organizations`, `consumers`
    y otros inquilinos); descubrimiento con caché (verifica que el emisor sea el del inquilino);
    `begin()` con `state` y `nonce` de 256 bits, PKCE S256 y alcances `openid profile email`;
    canje con Authlib (`AsyncOAuth2Client`, `client_secret_post`); validación del ID token con
    PyJWT (solo RS256, `kid` del JWKS con nueva descarga ante rotación, `iss`, `aud`, `nonce` en
    tiempo constante, `exp`, claims obligatorios y `tid` del inquilino → `TenantNotAllowedError`);
    devuelve solo `tid`, `oid`, `name` y `email` (o `preferred_username`). Errores:
    `IdpUnavailableError` (red, 5xx, 429) y `LoginFailedError` (código o token inválidos).
    Desviación menor de R-10: Authlib hace el canje y PyJWT (ya dependencia) valida el token.
    Override de mypy acotado al módulo por falta de tipos de Authlib. 20 pruebas en verde con
    respx y claves RSA generadas. Aviso: Authlib 1.8 emite una advertencia propia (migración a
    `httpx2`) que no se puede filtrar desde pytest; revisar al actualizar Authlib.
- [x] T078 [US1] Implementar `backend/src/saber_uli/identity/api/microsoft_router.py` (login y callback) para que pase T073 → Opus
  - Terminado: T073 en verde.
  - Estado: implementadas por Opus (2026-10-07); T073 falló al no existir las rutas (commit
    `468d4a1`). `microsoft_router`: `/login` guarda `state`, `nonce`, verificador PKCE y
    `return_to` (solo rutas internas: rechaza `//…`, `/\…` y URL absolutas) en `su_oidc`
    (firmada, `HttpOnly`, `SameSite=Lax`, `/api/auth/microsoft`, 10 min; `Secure` cuando
    `PUBLIC_BASE_URL` es https) y redirige a la autoridad del inquilino; `/callback` compara
    `state` en tiempo constante, borra la cookie (un solo uso), canjea y valida, crea o actualiza
    la cuenta, abre la sesión (cookie `su_refresh`) y redirige a `/bienvenida/datos`,
    `/bienvenida/perfil` o `return_to` (por defecto `/inicio`). Rechazos →
    `/ingresar?error=` con `tenant_not_allowed`, `idp_unavailable`, `invalid_state`,
    `login_cancelled`, `login_failed`, `account_disabled` o `account_deleted`, más el log
    `auth.login_rejected` con la causa (sin correo ni tokens). Límite 30/min por IP en ambas
    rutas. `main.py` arma `EntraIdClient` (redirect `PUBLIC_BASE_URL/api/auth/microsoft/callback`)
    y `AuthenticateInstitutionalUser`. 12 pruebas en verde con la app completa.
  - Desviación de R-13: `SessionMiddleware` firma la cookie `su_oidc` pero no la cifra. Se acepta:
    `state`, `nonce` y verificador son del propio navegador que inicia el flujo.
- [x] T079 [US1] Implementar `backend/src/saber_uli/identity/application/queries/get_me.py` y `backend/src/saber_uli/identity/api/me_router.py` para que pase T074; agregar `startMicrosoftLogin`, `completeMicrosoftLogin` y `getMe` a `backend/tests/contract/implemented_operations.py` → Qwen
  - Terminado: T074 y la prueba de contrato en verde.
  - Estado: implementadas por Opus (2026-10-07) porque Qwen no tenía créditos; T074 falló al no
    existir la ruta (commit `b3e7b2e`). `GetMe` (estado combinado con el acceso de invitado
    `guest_expired`/`guest_revoked`; roles y permisos ordenados; `consent_required` y
    `current_policy_version_id`; `profile_required` según `onboarding_completed_at`;
    `validated_at` + 7 días; vencimiento del acceso de invitado; `privileged_session`) y
    `me_router` con modelos del esquema `Me`; `main.py` monta `/api/v1` con la guardia de
    consentimiento (`getMe` exenta). `GuestAccessReader.expires_at_for` nuevo. Contrato: agregadas
    `startMicrosoftLogin`, `completeMicrosoftLogin` y `getMe`; el arnés usa un Entra ID simulado
    (ninguna prueba llama a Microsoft), no sigue redirecciones, excluye las comprobaciones 2xx/4xx
    en las dos operaciones que solo documentan 302 y usa un limitador sin límite (los límites se
    prueban en T035). Hallazgos del contrato corregidos en el router de T078: `return_to` inválido
    o de más de 200 caracteres se ignora (antes 422) y la falta de `state` redirige a
    `invalid_state` (antes 422). Además, el callback ya no tiene límite propio (el contrato no
    documenta 429 ahí): solo avanza con la cookie firmada de un solo uso que emite `/login`, que sí
    tiene el límite de 30/min por IP (precisión de R-31). T074 (7 pruebas) y contrato en verde;
    suite: 433.
- [x] T080 [US1] Implementar `frontend/src/features/auth/LoginPage.tsx` y `frontend/src/features/auth/bootstrap.ts` (tras volver de Microsoft: renovar, consultar `/me`, guardar instantánea, redirigir según guardias; botón de cerrar sesión en `AppShell`) → Qwen
  - Terminado: T075 en verde.
  - Estado: implementadas por Opus (2026-10-07) porque Qwen no tenía créditos; T075 falló al no
    existir los módulos (commit `40548c5`). `LoginPage` en `/ingresar` (búsqueda validada
    `error` y `return_to`): botón "Ingresar con mi cuenta Unilibre" que navega a
    `/api/auth/microsoft/login` (con `return_to` si lo hay), mensaje en `role="alert"` para cada
    código del backend (con la alternativa de pedir invitación ante `tenant_not_allowed`, SC-008,
    y uno genérico para códigos desconocidos) y enlace al ingreso de invitados (`/acceso`).
    `bootstrap.ts`: `startMicrosoftLogin` y `logout` (revoca en el servidor y siempre borra el
    token en memoria y la instantánea de Dexie). La ruta raíz pasa `session` al contexto; el
    `AppShell` muestra "Cerrar sesión" con sesión, invalida la caché de sesión y vuelve a
    `/ingresar`. Tras volver de Microsoft, el cargador de sesión de T067 renueva, consulta `/me`,
    guarda la instantánea y aplica las guardias. Frontend: 112 pruebas en verde.
- [x] T081 [US1] Prueba e2e `frontend/tests/e2e/us1-institutional-login.spec.ts` (usuario del inquilino llega a `/bienvenida/datos`; usuario externo ve el rechazo y no se crea cuenta; cerrar sesión exige ingresar de nuevo; axe sin infracciones AA en `/ingresar`) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07) porque Qwen no tenía créditos.
    `tests/e2e/us1-institutional-login.spec.ts` contra el stack real con perfil `e2e`: el usuario
    del inquilino llega a `/bienvenida/datos`; la cuenta externa ve el rechazo con la alternativa
    de invitación y no queda con sesión; cerrar sesión exige ingresar de nuevo; `/ingresar` sin
    infracciones de axe AA. En verde 3 corridas seguidas (Pixel 7). En WebKit se omite salvo con
    `E2E_OIDC_RESOLVES=1` (CI, con `127.0.0.1 oidc` en el archivo hosts); Chromium resuelve
    `oidc` con `--host-resolver-rules`. Hallazgos y correcciones:
    (1) `mock-oauth2-server` 3.0.3 no sustituye `${subject}`: la configuración solo fija `tid` y la
    fixture envía `oid`, `email` y `name` explícitos;
    (2) límites de R-31 incompatibles con el NAT del campus (429 en la renovación): ingreso 120/min
    por IP y renovación 30/min por sesión más 600/min por IP (research R-31 actualizado);
    (3) `auth.login_rejected` registra ahora el motivo de `login_failed`/`idp_unavailable` (mensajes
    fijos y clase del error de la biblioteca, sin valores del token);
    (4) el health check de `db` en Compose tiene más margen (60 s de arranque, 20 intentos): el
    primer arranque con los scripts de inicio superaba el anterior en un equipo cargado.
- [x] T082 [US1] Revisión de US1 (T071–T081) en `specs/001-identidad-acceso/tasks.md`: validación OIDC, ausencia de datos personales en logs, mensajes de error y cumplimiento de FR-001 a FR-005 y FR-036 → Opus
  - Terminado: tareas aprobadas y marcadas; quickstart V2 verificado.
  - Revisión de Opus (2026-10-07): T071–T081 aprobadas.
    - Validación OIDC: autoridad del inquilino (configuración y adaptador; el emisor del
      descubrimiento debe ser el del inquilino), PKCE S256, `state` en tiempo constante con cookie
      firmada de un solo uso (también evita el login CSRF), ID token solo RS256 con `kid`, `iss`,
      `aud`, `exp`/`nbf`, `nonce` en tiempo constante y `tid`; `return_to` solo interno y aplicado
      tras completar el primer ingreso. Riesgo bajo aceptado: un `kid` desconocido provoca una sola
      descarga del JWKS (el callback exige la cookie emitida por `/login`, que tiene límite).
    - Datos personales en logs (FR-036): `auth.login_rejected` con causa y motivo técnico,
      `auth.login_succeeded` solo con `user_id`; verificado en T073 sobre los logs JSON.
    - Mensajes: cada código de `/ingresar?error=` tiene texto propio en es-CO, con la alternativa
      de invitación para cuentas externas (SC-008); los códigos desconocidos usan un texto fijo
      (no se refleja la consulta).
    - FR-001 a FR-005: ingreso con Microsoft (T078, T081), rechazo de otro inquilino sin crear
      cuenta (T071, T073, T081), cuenta institucional con Estudiante (T071), solo `oid`, `tid`,
      nombre y correo (T072), reutilización por (`tid`, `oid`) con nombre y correo actualizados
      (T071).
    - **Corregido en la revisión**: dos primeros ingresos simultáneos de la misma persona (dos
      pestañas) terminaban en 500 por la restricción única; el repositorio la traduce a
      `UserAlreadyExistsError` y el caso de uso reintenta una vez (pruebas nuevas en T071 y T043).
    - Quickstart V2 verificado con las pruebas automáticas (mensaje con alternativa de invitación,
      sin cuenta nueva, log `tenant_not_allowed` sin correo). Para T177: el quickstart debe
      documentar `127.0.0.1 oidc` en el archivo hosts para e2e y la respuesta de `/api/ready` con
      `checks`.

**Checkpoint**: US1 funciona y se demuestra sola.

---

## Phase 4: User Story 2 - Autorización de tratamiento de datos (Priority: P1)

**Goal**: aceptar o rechazar de forma explícita la política, consultarla y revocarla; sin
autorización vigente no se usa la plataforma; una versión nueva exige aceptarla de nuevo.

**Independent Test**: usuario nuevo rechaza (sin acceso), acepta (acceso), consulta y revoca
(acceso suspendido); el administrador publica la versión 1.1 y se exige aceptarla.

### Tests for User Story 2 ⚠️

- [x] T083 [P] [US2] Prueba: semilla de la política en `backend/tests/integration/identity/test_policy_seed.py` (tras migrar existe la versión `1.0` vigente con el texto de `backend/seeds/politica_tratamiento_datos_v1.md`; volver a migrar no la duplica) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07) porque Qwen no tenía créditos. Verifica título,
    texto idéntico al archivo, vigencia y que volver a aplicar 0005 (`stamp 0004` + `upgrade`) no
    duplica. Se agregó `stamp_migrations` a `shared/infrastructure/migrations.py`.
- [x] T084 [P] [US2] Prueba: reglas de autorización en `backend/tests/unit/identity/test_consent.py` (decisión solo `accepted` o `rejected` sobre la versión vigente; revocar solo si hay autorización vigente (`no-active-consent`); decisión sobre versión no vigente → `policy-version-not-current`; publicar versión exige `version` con patrón `^[0-9]+\.[0-9]+$`, `body_markdown` de 200 a 100 000 caracteres y versión única) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Además del alcance: `revoked` no es una decisión
    válida (`invalid-consent-decision`, 422), sin política publicada no se puede decidir, y el
    título es obligatorio con máximo 200 caracteres (contrato).
- [x] T085 [P] [US2] Prueba: API en `backend/tests/integration/identity/test_consent_api.py` (`GET/POST /api/v1/me/consents` registra usuario, fecha, versión, decisión y canal `web_pwa` (FR-015); `POST /api/v1/me/consents/revocation` incrementa `auth_epoch` y la siguiente petición responde 401 (escenario 2.5); `GET /api/v1/privacy-policy/current` y `/versions/{id}` sin autenticación; `POST /api/v1/admin/privacy-policy/versions` exige `policy:publish` y sesión privilegiada y audita `policy.published`; tras publicar, `/me` devuelve `consent_required=true` para todos (FR-017); auditoría `consent.accepted|rejected|revoked`) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 18 casos. Las rutas de administración también
    pasan por la guardia de FR-014: el administrador debe tener la autorización vigente para
    publicar. `committed_login` ahora borra también las versiones que publicaron sus usuarios.
- [x] T086 [P] [US2] Pruebas de componente `frontend/src/features/onboarding/ConsentPage.test.tsx` (muestra finalidad, datos, derechos y canales; opciones "Acepto" y "No acepto" sin preselección; "No acepto" muestra la explicación con las opciones de aceptar luego o solicitar supresión) y `frontend/src/features/account/ConsentSettingsPage.test.tsx` (versión aceptada, fecha, ver texto, revocar con confirmación) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: implementada por Opus (2026-10-07). 12 casos entre las dos páginas, más un caso de
    guardia: sin autorización se puede abrir `/mi-cuenta/datos` (supresión, FR-014).

### Implementation for User Story 2

- [x] T087 [US2] Registrar en `specs/001-identidad-acceso/research.md` la dependencia `react-markdown` (sin `rehype-raw`, HTML deshabilitado) para mostrar la política de forma segura, con justificación y alternativas → Opus
  - Terminado: entrada nueva en research.md; ningún otro artefacto de diseño cambia.
  - Estado: hecho por Opus (2026-10-07): R-40 en research.md (`react-markdown` 10, sin
    `rehype-raw`, `skipHtml`, filtro de URL por defecto; alternativas `marked` + DOMPurify,
    texto plano y `markdown-to-jsx`).
- [x] T088 [US2] Implementar la migración `backend/migrations/versions/0005_seed_policy_v1.py` (carga idempotente de la versión 1.0) para que pase T083 → Qwen
  - Terminado: T083 en verde.
  - Estado: implementada por Opus (2026-10-07). `INSERT … ON CONFLICT (version) DO NOTHING` con
    `effective_from = now()`; el `downgrade` conserva la 1.0 si ya hay decisiones sobre ella. La
    imagen copia `backend/seeds` a `/app/seeds` (`.dockerignore` deja pasar `backend/seeds/*.md`).
    Las pruebas que creaban versiones con `effective_from` de hace días ahora usan
    `clock_timestamp()` para quedar después de la 1.0 sembrada.
  - Pendiente fuera del código: el texto sembrado es el BORRADOR de la política; la oficina
    jurídica debe aprobarlo antes de usar la app con usuarios reales (se publica la versión
    aprobada como 1.1 o 2.0 desde la administración).
- [x] T089 [US2] Implementar `backend/src/saber_uli/identity/domain/policy.py` y completar `backend/src/saber_uli/identity/domain/consent.py` para que pase T084 → Qwen
  - Terminado: T084 en verde.
  - Estado: implementada por Opus (2026-10-07). `domain/policy.py` (`PolicyVersion.publish`,
    `invalid-policy-version` 422, `policy-version-exists` 409) y en `consent.py`
    `decide_consent`, `revoke_consent`, canal `web_pwa` y los errores `policy-version-not-current`
    y `no-active-consent` (409).
- [x] T090 [US2] Implementar `backend/src/saber_uli/identity/application/consent.py` (decidir, revocar con incremento de `auth_epoch`, publicar), `backend/src/saber_uli/identity/api/consent_router.py` y `backend/src/saber_uli/identity/api/policy_router.py` para que pase T085; agregar las 6 operaciones a `implemented_operations.py` → Qwen
  - Terminado: T085 y la prueba de contrato en verde.
  - Estado: implementada por Opus (2026-10-07). `ConsentService` (historial, decidir, revocar:
    `auth_epoch` + 1, sesiones revocadas con `access_changed`, evento `UserAccessChanged`) y
    `PrivacyPolicyService` (vigente, por id, publicar con `policy:publish` + sesión privilegiada);
    puertos `ConsentRepository` (antes `ConsentReader`) y `PolicyRepository`. Auditoría con solo
    el número de versión. Contrato en verde con 13 operaciones.
  - Decisiones de Opus por hallazgos del contrato (commit 75860dc): el 405 lista en `Allow` los
    métodos de todas las rutas con la misma URL; un cuerpo ilegible responde 422 en vez de 400;
    un id mal formado en la ruta responde 404 (no nombra ningún recurso). El contrato agrega el
    422 de `decideConsent` (cuerpo inválido), que faltaba.
- [x] T091 [P] [US2] Implementar `frontend/src/features/onboarding/ConsentPage.tsx` y `frontend/src/features/account/ConsentSettingsPage.tsx` (Markdown con `react-markdown`) para que pase T086 → Qwen
  - Terminado: T086 en verde.
  - Estado: implementada por Opus (2026-10-07). `ConsentPage` (radios sin preselección,
    confirmación explícita, explicación al no aceptar con «revisar y aceptar» y enlace a la
    supresión; si la versión cambió, avisa y recarga) y `ConsentSettingsPage` (vigente, texto de
    esa versión, historial y revocación con `alertdialog`; al revocar borra el token y la
    instantánea sin conexión). `shared/ui/PolicyMarkdown.tsx` aplica R-40; `/mi-cuenta/datos` es
    un marcador hasta US7/US8 y el menú muestra «Mi autorización de datos».
- [x] T092 [P] [US2] Implementar `frontend/src/features/admin/PolicyPage.tsx` con su prueba `frontend/src/features/admin/PolicyPage.test.tsx` (publicar versión con vista previa; validación de versión y longitud) → Qwen
  - Terminado: prueba en verde.
  - Estado: implementada por Opus (2026-10-07). react-hook-form + zod con los límites del
    contrato, contador de caracteres, vista previa con `PolicyMarkdown` y vigencia en hora de
    Colombia (`-05:00`). Tras publicar invalida la sesión: quien publica también debe aceptar.
- [x] T093 [US2] Prueba e2e `frontend/tests/e2e/us2-consent.spec.ts` (V3 y V4 de quickstart: rechazar bloquea todo salvo política, cierre de sesión y supresión; aceptar da acceso; revocar cierra la sesión en la siguiente acción; nueva versión exige aceptación) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07). V3 en `us2-consent.spec.ts` (rechazo con
    explicación, guardias, supresión accesible, cierre de sesión; aceptar, consultar, revocar con
    `refresh` → 401 y nueva autorización al volver a ingresar) y V4 en
    `us2-policy-version.global.spec.ts`, en el proyecto `estado-global` de Playwright (corre
    después de los demás y sin paralelismo, porque cambia la versión vigente para todos). axe sin
    infracciones en las tres pantallas. `fixtures/db.ts` otorga el rol Administrador y completa
    el perfil con `psql` en el contenedor `db` hasta que existan `grant-admin` (T147) y US3. En
    verde 3 corridas completas seguidas (Pixel 7).
  - Hallazgo corregido (commit 11a42a8): dos versiones con la misma `effective_from` dejaban la
    vigente ambigua y una fecha anterior a la última nunca regía. Ahora 422
    `effective-from-too-early`, desempate por `created_at` y vigencia con segundos en el
    formulario.
- [x] T094 [US2] Revisión de US2 (T083–T093) en `specs/001-identidad-acceso/tasks.md`: Ley 1581 (autorización expresa, finalidad, versiones), FR-014 a FR-018 y SC-002 → Opus
  - Terminado: tareas aprobadas y marcadas.
  - Revisión de Opus (2026-10-07): T083–T093 aprobadas.
    - Ley 1581 (art. 9, autorización previa, expresa e informada): la decisión es explícita
      (radios sin preselección y confirmación), queda con usuario, fecha y hora, versión, decisión
      y canal `web_pwa` en `consents` (solo inserción para `saber_app`); la revocación es un
      registro más y nunca borra la prueba de la autorización. Finalidad, datos, derechos y
      canales vienen del texto de la política (FR-016), que se versiona (FR-017).
    - FR-014: la guardia de `/api/v1` responde 403 `consent-required` salvo `getMe`, decidir,
      consultar, revocar y supresión; política pública; la interfaz solo deja
      `/bienvenida/datos` y `/mi-cuenta/datos`. Aplica también a administración: quien publica
      debe aceptar su propia versión.
    - FR-015/FR-018: verificados por T084/T085 (unidad e integración) y T086/T093 (interfaz y
      e2e). Revocar sube `auth_epoch`, revoca las sesiones y la siguiente petición es 401; en el
      dispositivo se borran el token y la instantánea sin conexión.
    - SC-002: ningún usuario activo usa funciones sin una autorización vigente con fecha y versión
      (guardia en el servidor; la interfaz es solo ayuda).
    - Seguridad: Markdown sin HTML (R-40), publicar exige `policy:publish` y sesión privilegiada,
      auditoría sin datos personales (solo el número de versión).
    - Riesgos aceptados: (1) dos administradores que publiquen a la vez podrían pasar la
      validación de vigencia; la restricción única de `version` sigue protegiendo y el efecto es
      solo de orden (acción rara y auditada). (2) Un dispositivo sin conexión en el que no se
      revocó puede seguir mostrando contenido ya descargado hasta 7 días (R-17); no puede
      sincronizar y en la siguiente conexión recibe 401.
    - Pendiente fuera del código: aprobación jurídica del texto de la política (ver T088).

**Checkpoint**: US1 + US2 funcionan; ningún usuario usa la plataforma sin autorización vigente.

---

## Phase 5: User Story 3 - Completar el perfil en el primer ingreso (Priority: P1)

**Goal**: el institucional completa solo programa, semestre, fecha de presentación y meta
diaria; el invitado, solo nombre, meta y fecha opcional; ambos pueden editarlo después.

**Independent Test**: tras autorizar, completar el perfil y llegar a `/inicio` en menos de
1 minuto desde el inicio del ingreso; editarlo desde `/mi-cuenta`.

### Tests for User Story 3 ⚠️

- [x] T095 [P] [US3] Prueba: perfil en `backend/tests/unit/identity/test_profile.py` (institucional completo exige `program_id`, `semester` entre 1 y 12, `expected_exam_date` y `daily_goal` en `casual|regular|intense`; invitado completo exige `guest_display_name` de 2 a 120 caracteres y `daily_goal`, con `expected_exam_date` opcional, y rechaza `program_id` y `semester`; programa inactivo rechazado) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 26 casos. Además del alcance: quien ya tiene un
    programa que luego se desactivó puede conservarlo al editar; cambiar a otro inactivo no.
- [x] T096 [P] [US3] Prueba: API en `backend/tests/integration/identity/test_profile_api.py` (`GET /api/v1/programs` solo activos; `GET/PUT /api/v1/me/profile`; completar fija `onboarding_completed_at` y `/me` devuelve `profile_required=false`; nombre y correo institucionales no son editables (FR-021); 403 `consent-required` sin autorización) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 15 casos, incluidos los dos envíos simultáneos
    del primer perfil (doble toque) sin error 500 y el nombre del invitado como nombre visible.
- [x] T097 [P] [US3] Prueba de componente `frontend/src/features/onboarding/ProfilePage.test.tsx` (variante institucional con nombre y correo de solo lectura y cuatro campos; variante invitado con nombre, meta y fecha opcional; errores accesibles por campo) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 8 casos (institucional e invitado); la prueba de
    `AccountPage` (3 casos) se agregó con T101.
- [x] T098 [P] [US3] Prueba: comando `saber-uli identity import-programs --csv <archivo>` en `backend/tests/integration/identity/test_cli_import_programs.py` (CSV UTF-8 con encabezado `codigo,nombre,seccional`; `code` con patrón `^[A-Z0-9-]{2,20}$`, `name` de 3 a 200 caracteres, `campus` de 2 a 100; inserta o actualiza por `code` sin duplicar al repetir la carga; reporta filas inválidas sin abortar las válidas; audita `program.created` y `program.updated` con actor `system`) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 6 casos: CSV con BOM de Excel, carga repetible,
    filas inválidas con su número (incluye código repetido y columnas incompletas), encabezado
    distinto, errores de uso y ningún mensaje con la contraseña.

### Implementation for User Story 3

- [x] T099 [US3] Implementar `backend/src/saber_uli/identity/domain/profile.py` para que pase T095 → Qwen
  - Terminado: T095 en verde.
  - Estado: implementada por Opus (2026-10-07). `domain/profile.py` (`Profile.update` reemplaza
    el perfil completo según el tipo de cuenta; `invalid-profile` y `program-not-available`, 422).
- [x] T100 [US3] Implementar `backend/src/saber_uli/identity/infrastructure/repositories/programs.py`, `backend/src/saber_uli/identity/application/profile.py` y `backend/src/saber_uli/identity/api/profile_router.py` para que pase T096; agregar `listActivePrograms`, `getMyProfile`, `updateMyProfile` a `implemented_operations.py` → Qwen
  - Terminado: T096 y la prueba de contrato en verde.
  - Estado: implementada por Opus (2026-10-07). `ProfileService`, `ProgramCatalog`,
    repositorios de perfiles (con `ON CONFLICT` en el primer guardado) y programas, y
    `domain/program.py`; `User.complete_onboarding` y `User.rename_guest`. Sin perfil, `GET`
    devuelve `daily_goal=regular` y `complete=false` (el contrato exige la meta). Contrato en
    verde con 16 operaciones; en `updateMyProfile` se excluye `positive_data_acceptance` porque
    las reglas entre campos (institucional frente a invitado) solo están en la descripción.
- [x] T101 [US3] Implementar `frontend/src/features/onboarding/ProfilePage.tsx` y `frontend/src/features/account/AccountPage.tsx` (edición del perfil) para que pase T097 → Qwen
  - Terminado: T097 en verde.
  - Estado: implementada por Opus (2026-10-07). `features/profile/ProfileForm.tsx` y
    `DirectoryData.tsx` compartidos; `ProfilePage` en `/bienvenida/perfil` y `AccountPage` en
    `/mi-cuenta` (con enlaces a la autorización y a mis datos). El menú muestra «Mi cuenta».
- [x] T102 [US3] Implementar el comando `import-programs` en `backend/src/saber_uli/cli.py` y el caso de uso `backend/src/saber_uli/identity/application/import_programs.py` para que pase T098; documentado en quickstart.md §3 → Qwen
  - Terminado: T098 en verde.
  - Estado: implementada por Opus (2026-10-07). `saber-uli identity import-programs --csv`
    con `DATABASE_URL` (saber_app); salida 0, 1 (filas rechazadas o error de base de datos) o 2
    (archivo o configuración inválidos, nada cargado). No cambia el estado activo de los
    existentes. Ejemplo y códigos de salida en quickstart §3.
- [x] T103 [US3] Prueba e2e `frontend/tests/e2e/us3-first-login.spec.ts` (V1 de quickstart: ingreso, autorización y perfil hasta `/inicio` en menos de 60 s medidos por la prueba (SC-001); cerrar la app a mitad del primer ingreso y retomarlo en el paso pendiente (FR-022); editar el perfil) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07). V1 mide el tiempo desde el ingreso hasta
    `/inicio` (menos de 60 s; en local, unos 3 s); FR-022 cierra y reabre la app antes y después
    de autorizar; edición desde `/mi-cuenta` con recarga. axe sin infracciones. En verde 4
    corridas completas seguidas.
  - Hallazgo corregido (commit e03ca90): cerrar la app mientras se renovaba la sesión dejaba la
    cookie anterior y al volver se revocaba la sesión por «reutilización». Ahora hay un margen de
    30 s (precisión de R-14).
- [x] T104 [US3] Revisión de US3 (T095–T103) en `specs/001-identidad-acceso/tasks.md`: FR-019 a FR-022 y SC-001 → Opus
  - Terminado: tareas aprobadas y marcadas.
  - Revisión de Opus (2026-10-07): T095–T103 aprobadas.
    - FR-019: el institucional completa solo programa (del catálogo activo), semestre 1–12,
      fecha estimada y meta; el servidor valida igual que la interfaz.
    - FR-020: el invitado completa nombre (2–120), meta y fecha opcional; nunca programa ni
      semestre; su nombre pasa a ser su nombre visible.
    - FR-021: nombre y correo institucionales no viajan en `ProfileUpdate` (`additionalProperties:
      false` → 422) y la interfaz los muestra de solo lectura.
    - FR-022: el paso pendiente sale de `/me` (`consent_required`, `profile_required`) y la
      guardia lo aplica en cada carga; la e2e cierra y reabre la app en ambos pasos.
    - SC-001: medido por la e2e (muy por debajo de 60 s).
    - Correcciones hechas en la revisión: margen de reutilización del token de renovación (R-14)
      y primer perfil con doble envío sin error 500.
    - Pendiente fuera del código: cargar el catálogo real de programas de todas las seccionales
      con `import-programs` antes de abrir la app a estudiantes.

**Checkpoint**: MVP institucional completo (US1 + US2 + US3).

---

## Phase 6: User Story 4 - Acceso de invitados (Priority: P2)

**Goal**: un invitado entra con el enlace de su correo, sin contraseña; puede pedir enlaces de
ingreso nuevos; su acceso vence o se revoca de forma efectiva.

**Independent Test**: crear una invitación con el comando CLI, abrir el correo en Mailpit, pulsar
"Ingresar", verificar las restricciones y verificar que tras vencer no entra.

### Tests for User Story 4 ⚠️

- [x] T105 [P] [US4] Prueba: acceso del invitado en `backend/tests/unit/identity/test_invitation_access.py` (aceptar crea un usuario `guest` solo con rol `guest` y pasa la invitación a `accepted`; acceso vigente si `accepted`, sin `revoked_at` y `access_expires_at` futuro; fin de acceso = mínimo entre revocación y vencimiento; vencido → `guest-access-expired`; revocado → `guest-access-revoked`) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 17 casos sobre `domain/invitation.py`.
- [x] T106 [P] [US4] Prueba: enlaces de acceso en `backend/tests/unit/identity/test_access_links.py` (token de 256 bits; se guarda solo su SHA-256; un solo uso; vigencia `invitation` 7 días y `sign_in` 15 minutos tomadas de los parámetros; emitir uno nuevo invalida los anteriores sin usar del mismo propósito; research R-18 y R-19) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 11 casos: entropía y formato del token, solo
    hash, vigencias desde los parámetros, un solo uso y reemplazo de enlaces sin usar.
- [x] T107 [P] [US4] Prueba: `POST /api/auth/guest/sessions` en `backend/tests/integration/identity/test_guest_session_api.py` (token válido de invitación → crea invitado, abre sesión y fija la cookie; token usado o vencido → 400 `access-link-invalid`; acceso vencido → 403 `guest-access-expired`; revocado → 403 `guest-access-revoked`; 60/min por IP (precisión de R-31); escenarios 4.1, 4.3 y 4.4) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 10 casos con la fixture `guests`
    (`tests/integration/identity/guests.py`): enlace válido crea al invitado y abre la sesión
    (`guest_link`), enlace usado, vencido o desconocido → 400, acceso vencido o revocado → 403,
    enlace de ingreso con la cuenta existente y límite por IP (60/min tras la precisión de R-31).
- [x] T108 [P] [US4] Prueba: `POST /api/auth/guest/link-requests` en `backend/tests/integration/identity/test_sign_in_link_request.py` (siempre 202 con el mismo cuerpo exista o no el correo (FR-013); solo un invitado vigente genera `identity.SignInLinkRequested`; el payload del outbox no contiene correo ni token; límites 5/h por hash de correo y 20/h por IP) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 8 casos: evento solo para invitados vigentes
    (no pendientes, vencidos ni revocados), cuerpo idéntico, payload sin correo ni token y los dos
    límites con IP y correo controlados.
- [x] T109 [P] [US4] Prueba: manejador del worker en `backend/tests/integration/identity/test_sign_in_link_handler.py` (al procesar `SignInLinkRequested` emite el enlace, envía el correo a Mailpit con URL `<PUBLIC_BASE_URL>/acceso#t=<token>`, y el token en claro no aparece en base de datos, outbox, Redis ni logs) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 4 casos con Mailpit real (fixture `mailpit`
    compartida en `tests/integration/conftest.py`): enlace de ingreso y de invitación, reemplazo
    del enlace anterior y nada enviado si el acceso cambió entre la solicitud y el envío; el token
    no aparece en `access_links`, outbox, Redis ni logs.
- [x] T110 [P] [US4] Prueba: fachada para otros contextos en `backend/tests/unit/identity/test_public_facade.py` (`is_institutional(user_id)` y `is_guest(user_id)` para excluir invitados de ligas y analítica en specs futuras, FR-012) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 2 casos con los dobles en memoria.
- [x] T111 [P] [US4] Prueba: comando `saber-uli identity invite-guest --email --days` en `backend/tests/integration/identity/test_cli_invite_guest.py` (crea invitación con actor `system`, rechaza dominios institucionales, encola `InvitationCreated`) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 5 casos por subproceso: actor sistema, auditoría
    y evento en el outbox; plazo por defecto; dominio institucional (con subdominios) rechazado;
    invitación vigente duplicada; datos de uso inválidos.
- [x] T112 [P] [US4] Pruebas de componente `frontend/src/features/auth/GuestAccessPage.test.tsx` (lee el token del fragmento, lo borra del historial, solo envía al pulsar "Ingresar", mensajes por causa) y `frontend/src/features/auth/GuestLinkRequestPage.test.tsx` (mismo mensaje exista o no el correo) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: implementada por Opus (2026-10-07). 10 casos entre las dos páginas. El enlace «Soy
    invitado» de `/ingresar` pasa a `/ingresar/invitado` (se ajustó la prueba de T075).

### Implementation for User Story 4

- [x] T113 [US4] Implementar `backend/src/saber_uli/identity/domain/invitation.py` (estado `sent → accepted` y reglas de acceso) para que pase T105 → Qwen
  - Terminado: T105 en verde.
  - Estado: implementada por Opus (2026-10-07). Los errores `guest-access-expired` y
    `guest-access-revoked` pasan al dominio; la guardia y la renovación los reutilizan.
- [x] T114 [US4] Implementar `backend/src/saber_uli/identity/domain/access_link.py` y `backend/src/saber_uli/identity/infrastructure/link_tokens.py` para que pase T106 → Opus
  - Terminado: T106 en verde.
  - Estado: implementada por Opus (2026-10-07). `secrets.token_urlsafe(32)` (43 caracteres) y
    SHA-256; `LinkTokenFactory` como adaptador del puerto `LinkTokenGenerator`.
- [x] T115 [US4] Implementar `backend/src/saber_uli/identity/application/guest_sessions.py` y `backend/src/saber_uli/identity/api/guest_router.py` (sesiones y solicitudes de enlace) para que pasen T107 y T108; agregar `createGuestSession` y `requestGuestSignInLink` a `implemented_operations.py` → Opus
  - Terminado: T107, T108 y la prueba de contrato en verde.
  - Estado: implementada por Opus (2026-10-07). `GuestSignIn` (enlace bloqueado con `FOR UPDATE`,
    acepta y crea al invitado o reutiliza su cuenta; si el acceso venció o fue revocado, nada se
    consume) y `RequestSignInLink`; `guest_router` (400 vía `STATUS_BY_SLUG`, 403 en este
    ingreso aunque en la renovación la causa sea 401). Eventos por el outbox con
    `register_identity_outbox`. Contrato en verde con 18 operaciones; se agregó el 422 de
    `createGuestSession` y su aceptación se excluye de `positive_data_acceptance` (un token bien
    formado pero desconocido es un 400 correcto).
- [x] T116 [US4] Implementar `backend/src/saber_uli/identity/infrastructure/handlers/link_emails.py` (manejadores de `SignInLinkRequested` e `InvitationCreated` que emiten el enlace y llaman a `notifications.application.public.send_email`) y las plantillas `backend/src/saber_uli/notifications/infrastructure/templates/{guest_invitation,guest_sign_in}.{html,txt}.j2` para que pase T109 → Opus
  - Terminado: T109 en verde.
  - Estado: implementada por Opus (2026-10-07). `LinkEmailHandlers` registrados en el worker con
    `EmailService` armado desde la configuración SMTP; plantillas `guest_invitation` y
    `guest_sign_in` (HTML y texto). Si el envío falla, `last_delivery_status = failed` y el
    despachador reintenta con un enlace nuevo.
- [x] T117 [P] [US4] Implementar `backend/src/saber_uli/identity/application/public.py` (fachada pública) para que pase T110 → Qwen
  - Terminado: T110 en verde; `lint-imports` pasa.
  - Estado: implementada por Opus (2026-10-07). `UserDirectory` en la fachada pública e
    `IdentityDirectory` en `application/directory.py`; `lint-imports` pasa.
- [x] T118 [P] [US4] Implementar el comando `invite-guest` en `backend/src/saber_uli/cli.py` y `backend/src/saber_uli/identity/application/invitations.py` (creación mínima) para que pase T111 → Qwen
  - Terminado: T111 en verde.
  - Estado: implementada por Opus (2026-10-07). `CreateInvitation` y el subcomando con salida 0,
    1 o 2. Migración 0006: `invitations.invited_by` admite NULL = sistema (data-model §2.7).
- [x] T119 [US4] Implementar `frontend/src/features/auth/GuestAccessPage.tsx` (`/acceso`) y `frontend/src/features/auth/GuestLinkRequestPage.tsx` (`/ingresar/invitado`) para que pase T112 → Qwen
  - Terminado: T112 en verde.
  - Estado: implementada por Opus (2026-10-07). `GuestAccessPage` (`/acceso`) y
    `GuestLinkRequestPage` (`/ingresar/invitado`).
- [x] T120 [US4] Prueba e2e `frontend/tests/e2e/us4-guest-access.spec.ts` (V5 y V6: invitación por CLI, correo en Mailpit, ingreso sin contraseña en menos de 2 minutos (SC-007), perfil de invitado, enlace reutilizado rechazado, nuevo enlace por correo, acceso vencido rechazado con fecha simulada) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07). V5 (invitación por CLI dentro del contenedor
    `api`, correo en Mailpit, ingreso hasta `/inicio` en menos de 2 min, restricciones, enlace
    reutilizado rechazado, enlace nuevo por correo) y V6 (acceso vencido con fecha simulada). Corre
    también en iPhone (no usa OIDC). En verde 3 corridas completas seguidas.
  - Hallazgos corregidos: la cookie `su_refresh` con `Secure` no se guardaba en WebKit sobre
    `http://localhost` (commit bb23210, precisión de R-14) y 10 ingresos por minuto por IP no
    alcanzaban para varios invitados tras la misma IP (commit e574fb0, precisión de R-31).
- [x] T121 [US4] Revisión de US4 (T105–T120) en `specs/001-identidad-acceso/tasks.md`: manejo de tokens, enumeración de correos, límites y FR-007, FR-011 a FR-013 → Opus
  - Terminado: tareas aprobadas y marcadas.
  - Revisión de Opus (2026-10-07): T105–T120 aprobadas.
    - Tokens: 256 bits, solo SHA-256 en la base, un solo uso con bloqueo de fila, vigencias de
      los parámetros; los genera el worker (el outbox lleva solo el id). El enlace usa el
      fragmento (no llega al servidor ni a los registros del proxy), la página lo borra del
      historial y solo lo envía al pulsar «Ingresar» (los escáneres de correo no lo gastan).
    - Enumeración de correos (FR-013): `link-requests` responde siempre 202 con el mismo cuerpo.
      Queda una diferencia de tiempo mínima (insertar el evento en el outbox); con 5/h por correo
      y 20/h por IP no es aprovechable. Los 400/403 de `guest/sessions` exigen un token válido.
    - Límites: R-31 con la precisión de 60/min por IP al consumir enlaces.
    - FR-007 (enlaces de un solo uso y corta duración, sin contraseña), FR-011 (vencido o revocado
      no entra ni renueva) y FR-013 cubiertos por T105–T109 y T120. FR-012 queda listo en la
      fachada para ligas y analítica (specs futuras).
    - Riesgo aceptado: el outbox entrega al menos una vez; si se repite un evento ya procesado,
      el invitado recibe un segundo correo y solo vale el último enlace.
    - Nota: los commits de T118, T116 y T115 se hicieron en ese orden y los dos primeros no
      compilan por separado (dependen de puertos que llegaron con T115).

**Checkpoint**: invitados entran y salen de forma segura.

---

## Phase 7: User Story 5 - Gestión de invitaciones (Priority: P2)

**Goal**: administradores y docentes envían invitaciones individuales y por lote, las reenvían,
cambian su vencimiento y las revocan; cada docente gestiona solo las suyas.

**Independent Test**: invitación individual y lote con filas inválidas, duplicadas e
institucionales; revisar el reporte; revocar y comprobar que el invitado pierde el acceso.

### Tests for User Story 5 ⚠️

- [x] T122 [P] [US5] Prueba: reglas de gestión en `backend/tests/unit/identity/test_invitation_management.py` (correo de `INSTITUTIONAL_EMAIL_DOMAINS` o sus subdominios → `institutional-email-not-invitable` (FR-008); docente con vencimiento mayor a `teacher_max_access_days` → `access-expiry-out-of-range`, administrador sin límite (FR-006a); sin vencimiento → `default_guest_access_days`; invitación vigente al mismo correo → `invitation-already-active`; reenviar solo si no está aceptada; revocar incrementa el `auth_epoch` del invitado; renovar dentro de 90 días desde el fin del acceso vuelve a `accepted` y limpia `retention_notice_sent_at`; invitado suprimido → `guest-erased`) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 20 casos sobre `InvitationService` con los
    dobles en memoria (incluye el alcance del docente: lo ajeno es `not-found`).
- [x] T123 [P] [US5] Prueba: lotes en `backend/tests/unit/identity/test_invitation_batch.py` (CSV UTF-8 con encabezado `correo,nombre,vence`, fecha `AAAA-MM-DD`; JSON equivalente; más de 500 filas → `batch-too-large`; resultado por fila `valid`, `invalid_email`, `duplicate_in_file`, `already_invited`, `institutional_email`, `expiry_out_of_range`; el lote vence a las 24 h; validar 500 filas en menos de 2 s) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 13 casos; «vence» es una fecha y el acceso dura
    hasta el final de ese día en Colombia; una fecha mal escrita queda como
    `expiry_out_of_range`.
- [x] T124 [P] [US5] Prueba: API de invitaciones en `backend/tests/integration/identity/test_invitations_api.py` (crear, listar con filtros `status`, `q` e `invited_by` (solo administrador), obtener, cambiar vencimiento, reenviar y revocar; un docente solo ve las suyas y las ajenas responden 404 (escenario 5.7); un estudiante recibe 403; todas exigen sesión privilegiada; cada acción audita `invitation.*`; revocar termina las sesiones abiertas del invitado (escenario 5.4)) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 12 casos con la fixture `staff`
    (`tests/integration/identity/staff.py`); `committed_login` borra también los lotes.
- [x] T125 [P] [US5] Prueba: API de lotes en `backend/tests/integration/identity/test_invitation_batches_api.py` (`POST /api/v1/invitation-batches` con CSV y con JSON devuelve el reporte; `POST /{id}/confirmation` crea solo las válidas, encola un `InvitationCreated` por fila y audita `invitation_batch.confirmed`; confirmar dos veces o vencido → 409 `batch-not-pending`; un docente no ve lotes ajenos) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 7 casos (CSV, JSON, confirmación con eventos y
    auditoría, 409 al repetir o vencer, alcance, 413 y encabezado inválido).
- [x] T126 [P] [US5] Prueba: tarea `expire_invitations` en `backend/tests/integration/identity/test_expire_invitations_task.py` (`sent` con enlace vencido → `expired`; `accepted` con acceso vencido → `expired` e incremento de `auth_epoch`; idempotente; `last_delivery_status` refleja `queued`, `sent` o `failed` del manejador; una invitación nunca aceptada pierde `email` e `invitee_name` y sus `access_links` 90 días después de `revoked_at` si fue revocada o, si no, de `link_expires_at`, y se audita `invitation.contact_purged` (FR-034e)) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). 6 casos; incluye el estado `failed` cuando el
    envío del correo falla.
- [x] T127 [P] [US5] Pruebas de componente `frontend/src/features/invitations/InvitationsPage.test.tsx` (lista con filtro por estado, acciones por fila, docente sin filtro `invited_by`), `InviteForm.test.tsx` (validación de correo y vencimiento máximo) y `BatchUpload.test.tsx` (carga de CSV, tabla del reporte por fila, confirmación) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: implementada por Opus (2026-10-07). 16 casos en las tres pruebas (con
    `features/invitations/testing.tsx`), más la búsqueda por correo o nombre agregada en la e2e.

### Implementation for User Story 5

- [x] T128 [US5] Completar `backend/src/saber_uli/identity/domain/invitation.py` (reenviar, revocar, cambiar vencimiento, renovar) para que pase T122 → Qwen
  - Terminado: T122 en verde.
  - Estado: implementada por Opus (2026-10-07). Dominio (`resend`, `revoke` que no se repite,
    `change_expiry` con renovación dentro de 90 días, `validate_access_expiry`) e
    `InvitationService` en `application/invitations.py`, que reemplaza a `CreateInvitation`.
    Errores nuevos: `invitation-already-revoked`, `invitation-not-renewable`, `guest-erased`.
- [x] T129 [US5] Implementar `backend/src/saber_uli/identity/domain/invitation_batch.py` y `backend/src/saber_uli/identity/application/invitation_batches.py` para que pase T123 → Qwen
  - Terminado: T123 en verde.
  - Estado: implementada por Opus (2026-10-07). `InvitationBatch` y `InvitationBatchService`;
    al confirmar se vuelve a comprobar cada fila (vencimiento y otra invitación creada en el
    intervalo).
- [x] T130 [US5] Completar `backend/src/saber_uli/identity/application/invitations.py` e implementar `backend/src/saber_uli/identity/api/invitations_router.py` (invitaciones y lotes, con alcance por `invited_by` en la consulta) para que pasen T124 y T125; agregar las 9 operaciones de invitaciones y lotes a `implemented_operations.py` → Qwen
  - Terminado: T124, T125 y la prueba de contrato en verde.
  - Estado: implementada por Opus (2026-10-07). `invitations_router` con las 9 operaciones; el
    lote acepta `text/csv` o JSON. Contrato en verde con 27 operaciones. El contrato deja
    `invited_by` en `null` para las invitaciones del sistema.
- [x] T131 [US5] Implementar las tareas `expire_invitations` en `backend/src/saber_uli/identity/infrastructure/tasks.py` y el registro de `last_delivery_status` en `backend/src/saber_uli/identity/infrastructure/handlers/link_emails.py` (reenvío con `InvitationResent`), incluida la purga de contacto de FR-034e, para que pase T126 → Qwen
  - Terminado: T126 en verde.
  - Estado: implementada por Opus (2026-10-07). `identity/infrastructure/tasks.py` y la tarea del
    worker (invalida la caché de épocas tras el commit). Además vence los lotes pendientes y borra
    los lotes de más de 30 días (data-model §2.9).
- [x] T132 [US5] Implementar `frontend/src/features/invitations/{InvitationsPage.tsx,InviteForm.tsx,BatchUpload.tsx,InvitationActions.tsx}` para que pase T127 → Qwen
  - Terminado: T127 en verde.
  - Estado: implementada por Opus (2026-10-07). Página `/invitaciones` con formulario, lote,
    filtro por estado, búsqueda, «solo las que yo envié» para administradores y acciones por
    fila. Además: sin sesión privilegiada ofrece «Confirmar mi identidad»; las consultas no
    reintentan errores 4xx; y si la renovación responde que el acceso del invitado fue revocado o
    venció (o la cuenta está desactivada o eliminada), la app vuelve a `/ingresar` con la causa
    (SC-003).
- [x] T133 [US5] Prueba e2e `frontend/tests/e2e/us5-invitations.spec.ts` (V7 a V12 de quickstart: correo institucional rechazado, tope del docente, lote de 200 filas en menos de 5 minutos (SC-005), alcance del docente, revocación inmediata, renovación con progreso conservado) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07). V7, V8, V10, V11 y V12 en
    `us5-invitations.spec.ts`; V9 en `us5-invitation-batch.global.spec.ts` (proyecto
    `estado-global`). `globalSetup` borra los contadores de límites antes de cada corrida. En
    verde 3 corridas completas seguidas.
- [x] T134 [US5] Revisión de US5 (T122–T133) en `specs/001-identidad-acceso/tasks.md`: alcance por docente sin fugas (404 en recursos ajenos), auditoría completa (SC-004), FR-006 a FR-010 → Opus
  - Terminado: tareas aprobadas y marcadas.
  - Revisión de Opus (2026-10-07): T122–T133 aprobadas.
    - Alcance sin fugas: el docente solo encuentra lo suyo en la consulta (listado, detalle,
      acciones y lotes); lo ajeno responde 404 (T122, T124, T125, V10). El filtro `invited_by`
      solo aplica a administradores.
    - Auditoría (SC-004): `invitation.created|resent|expiry_changed|revoked|accepted`,
      `invitation_batch.confirmed` e `invitation.contact_purged`, con actor y sin datos
      personales. El vencimiento automático lo hace el sistema y no es una acción
      administrativa.
    - FR-006/006a (plazo del docente al crear, al cambiar el vencimiento y en lotes), FR-007
      (enlaces del worker), FR-008 (subdominios incluidos), FR-009 (reporte por fila, solo las
      válidas, 500 filas), FR-010 (revocar termina las sesiones; cambiar el vencimiento aplica de
      inmediato) y FR-034e (purga a los 90 días) cubiertos.
    - Riesgos aceptados: (1) si otra invitación al mismo correo se crea justo durante la
      confirmación de un lote, la confirmación falla con 409 y se puede repetir; (2) el worker
      envía unos 6 correos por segundo, así que un lote de 500 demora los demás correos ~1,5 min.

**Checkpoint**: ciclo completo de invitados (US4 + US5).

---

## Phase 8: User Story 6 - Roles y grupos (Priority: P2)

**Goal**: el administrador asigna roles combinables, programas a directores, crea grupos con
estudiantes y docentes, desactiva cuentas, gestiona programas, parámetros y consulta auditoría.

**Independent Test**: asignar Docente y Director a un usuario, asociarlo a un grupo y verificar
la unión de permisos; retirar un rol y verificar que los pierde; intentar quitar el último
administrador.

### Tests for User Story 6 ⚠️

- [x] T135 [P] [US6] Prueba: reglas de roles en `backend/tests/unit/identity/test_role_rules.py` (un institucional conserva siempre `student` (`student-role-required`); `guest` es exclusivo (`guest-role-exclusive`); `program_director` exige al menos un programa (`director-requires-programs`); retirar `admin` o desactivar al último administrador activo → `last-admin`; retirar roles incrementa `auth_epoch`) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Reglas en `User.set_roles` (devuelve roles otorgados y
    retirados); `director-requires-programs` también exige que los programas existan
    (`unknown-program`).
- [x] T136 [P] [US6] Prueba de concurrencia en `backend/tests/integration/identity/test_last_admin_concurrency.py` (dos administradores se quitan el rol mutuamente en transacciones simultáneas: exactamente una falla; FR-025) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Dos transacciones simultáneas: exactamente una falla con
    `last-admin`, en 6 rondas seguidas.
- [x] T137 [P] [US6] Prueba: API de usuarios en `backend/tests/integration/identity/test_admin_users_api.py` (listar con filtros `q`, `kind`, `role` y `status`; obtener; `PATCH` de estado desactiva, termina sesiones y audita `user.disabled|reactivated`; `PUT /roles` audita `user.role_granted|role_revoked` con roles antes y después y `user.director_programs_changed`; solo administradores con sesión privilegiada) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Incluye `NotInstitutionalAccountError` al intentar roles
    institucionales sobre un invitado.
- [x] T138 [P] [US6] Prueba: grupos en `backend/tests/unit/identity/test_group.py` (miembros solo estudiantes institucionales (`not-institutional-student`), docentes solo con rol `teacher` (`not-a-teacher`), nombre de 2 a 120 caracteres, `cohort_label` hasta 20) y `backend/tests/integration/identity/test_groups_api.py` (CRUD y archivado, agregar y quitar miembros y docentes, auditoría `group.*`) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: implementada por Opus (2026-10-07). Unidad y API de grupos; auditoría `group.created|updated|archived`
    y `group.member_added|member_removed|teacher_added|teacher_removed`.
- [x] T139 [P] [US6] Prueba: vista del docente y del director en `backend/tests/integration/identity/test_teacher_groups_api.py` (`GET /api/v1/teacher/groups` solo grupos propios; `GET /teacher/groups/{id}/students` devuelve `display_name` sin correo y 404 en grupos ajenos (FR-027); un usuario solo `program_director` recibe 403 en endpoints que exponen nombres o correos (FR-026); la fachada `director_program_ids(user_id)` devuelve sus programas) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). El director sin rol Docente recibe 403 en usuarios, grupos,
    invitaciones y la vista del docente.
- [x] T140 [P] [US6] Prueba: programas, parámetros y auditoría en `backend/tests/integration/identity/test_admin_catalogs_api.py` (programas: `code` con patrón `^[A-Z0-9-]{2,20}$` único, `name` 3–200, `campus` 2–100, auditoría `program.*`; parámetros: rangos del contrato y auditoría `setting.changed`; auditoría: filtros `action`, `actor_id`, `subject_user_id`, `from`, `to` y orden descendente, solo lectura) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). `setting.changed` guarda `{key, before, after}`.
- [x] T141 [P] [US6] Prueba: comando `saber-uli identity grant-admin --email` en `backend/tests/integration/identity/test_cli_grant_admin.py` (solo sobre un institucional existente; audita con actor `system`; mensaje claro si no existe) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Mensaje claro si el correo no existe.
- [x] T142 [P] [US6] Pruebas de componente en `frontend/src/features/admin/UsersPage.test.tsx` (lista, editor de roles con programas del director, desactivar y reactivar, error `last-admin`), `frontend/src/features/admin/GroupsPage.test.tsx`, `frontend/src/features/admin/CatalogPages.test.tsx` (programas, parámetros, auditoría) y `frontend/src/features/teacher/TeacherGroupsPage.test.tsx` (nombres sin correo) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: implementada por Opus (2026-10-07). 188 pruebas de frontend en verde al cerrar T149.

### Implementation for User Story 6

- [x] T143 [US6] Completar `backend/src/saber_uli/identity/domain/user.py` (asignación de roles y programas del director) y el bloqueo de administradores en `backend/src/saber_uli/identity/infrastructure/repositories/users.py` para que pasen T135 y T136 → Qwen
  - Terminado: T135 y T136 en verde (T136 revisada por Opus).
  - Estado: implementada por Opus (2026-10-07). El bloqueo de administradores es en dos pasos:
    `SELECT … FOR UPDATE` y luego una consulta nueva que cuenta los activos. Con un solo paso,
    T136 falló en 5 de 6 rondas (la segunda transacción contaba con la fila vieja).
- [x] T144 [US6] Implementar `backend/src/saber_uli/identity/application/admin_users.py` y `backend/src/saber_uli/identity/api/admin_users_router.py` para que pase T137 → Qwen
  - Terminado: T137 en verde.
  - Estado: implementada por Opus (2026-10-07). Contrato: se agregó 422 a `adminUpdateUserStatus` y
    `adminSetUserRoles` (registrado en b76b0c2).
- [x] T145 [US6] Implementar `backend/src/saber_uli/identity/domain/group.py`, `backend/src/saber_uli/identity/application/groups.py`, `backend/src/saber_uli/identity/api/groups_router.py` y `backend/src/saber_uli/identity/api/teacher_router.py`, y `director_program_ids` en `backend/src/saber_uli/identity/application/public.py`, para que pasen T138 y T139 → Qwen
  - Terminado: T138 y T139 en verde.
  - Estado: implementada por Opus (2026-10-07). Contrato: 403 en las operaciones de grupos y 422 en
    `adminAddGroupMembers` y `adminAddGroupTeachers` (b76b0c2). Nueva operación
    `adminListGroupMembers` con `GroupMember`/`GroupMemberPage` (ee42b48), necesaria para que el
    administrador vea y quite miembros.
- [x] T146 [US6] Implementar `backend/src/saber_uli/identity/api/admin_catalogs_router.py` (programas, parámetros, auditoría) con sus casos de uso en `backend/src/saber_uli/identity/application/catalogs.py` para que pase T140; agregar las operaciones de usuarios, grupos, docente, programas, parámetros y auditoría a `implemented_operations.py` → Qwen
  - Terminado: T140 y la prueba de contrato en verde.
  - Estado: implementada por Opus (2026-10-07). Contrato en verde con 48 operaciones. Programas con código único
    (`program-code-exists`).
- [x] T147 [US6] Implementar el comando `grant-admin` en `backend/src/saber_uli/cli.py` para que pase T141 → Qwen
  - Terminado: T141 en verde.
  - Estado: implementada por Opus (2026-10-07). `saber-uli identity grant-admin --email`; audita
    `user.role_granted` con actor `system`.
- [x] T148 [P] [US6] Implementar `frontend/src/features/admin/{UsersPage.tsx,UserRolesEditor.tsx,GroupsPage.tsx,GroupDetail.tsx}` para que pasen sus pruebas de T142 → Qwen
  - Terminado: pruebas de usuarios y grupos en verde.
  - Estado: implementada por Opus (2026-10-07). `/admin/usuarios` con editor de roles y programas del director,
    desactivar y reactivar; `/admin/grupos` y `/admin/grupos/$groupId` con estudiantes y
    docentes. Sin sesión privilegiada ofrecen «Confirmar mi identidad».
- [x] T149 [P] [US6] Implementar `frontend/src/features/admin/{ProgramsPage.tsx,SettingsPage.tsx,AuditPage.tsx}` y `frontend/src/features/teacher/TeacherGroupsPage.tsx` para que pasen sus pruebas de T142 → Qwen
  - Terminado: pruebas de catálogos y docente en verde.
  - Estado: implementada por Opus (2026-10-07). `/admin/programas`, `/admin/parametros`, `/admin/auditoria` y
    `/grupos` (nombres sin correo). El menú muestra cada enlace solo con su permiso.
- [x] T150 [US6] Prueba e2e `frontend/tests/e2e/us6-roles-groups.spec.ts` (V13 a V15: unión de permisos, último administrador, vista del docente y del director, reautenticación tras 31 minutos de inactividad privilegiada sin interrumpir la práctica personal) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07). V13 (unión de permisos), V14 y V15 en
    `us6-roles-groups.spec.ts`; el último administrador en `us6-last-admin.global.spec.ts`
    (proyecto `estado-global`). En verde 3 corridas completas seguidas.
- [x] T151 [US6] Revisión de US6 (T135–T150) en `specs/001-identidad-acceso/tasks.md`: autorización y alcance (FR-023 a FR-030), datos visibles por rol, auditoría (SC-004) → Opus
  - Terminado: tareas aprobadas y marcadas.
  - Revisión de Opus (2026-10-07): T135–T150 aprobadas.
    - Autorización (FR-023 a FR-025): roles combinables con la unión de permisos; Estudiante
      fijo para el institucional e Invitado exclusivo; retirar un rol incrementa `auth_epoch` y
      la sesión pierde el permiso en la siguiente acción. El último administrador activo no
      puede perder el rol ni ser desactivado, también con transacciones concurrentes (T136).
    - Datos visibles por rol (FR-026, FR-027): el docente solo ve sus grupos y los nombres sin
      correo (404 en grupos ajenos); el director de programa sin otro rol no llega a ningún
      endpoint con nombres o correos (403), y la fachada `director_program_ids` queda para los
      reportes agregados.
    - FR-028 a FR-030: programas, parámetros y auditoría solo para administradores con sesión
      privilegiada (R-15: 30 minutos sin actividad privilegiada piden autenticarse de nuevo sin
      cortar la práctica personal, V15).
    - Auditoría (SC-004): `user.role_granted|role_revoked|director_programs_changed|disabled|
      reactivated`, `group.*`, `program.created|updated` y `setting.changed`, con actor y sin
      datos personales en los registros.
    - Cambios de contrato registrados: 403/422 adicionales (b76b0c2) y `adminListGroupMembers`
      (ee42b48).
    - Riesgo aceptado: los listados de administración cargan hasta 100 programas o miembros por
      página en el editor; basta mientras el catálogo sea pequeño.

**Checkpoint**: roles, grupos y administración completos.

---

## Phase 9: User Story 7 - Supresión de la cuenta y de los datos personales (Priority: P3)

**Goal**: el usuario solicita la supresión y pierde el acceso al instante; se completa en máximo
15 días hábiles; los invitados (90 días) e institucionales (1 año sin ingresar) se suprimen
automáticamente con aviso 30 días antes.

**Independent Test**: solicitar la supresión, confirmar, verificar que no puede ingresar, que sus
datos personales no aparecen y que todo quedó auditado; reingresar crea una cuenta nueva.

### Tests for User Story 7 ⚠️

- [x] T152 [P] [US7] Prueba: días hábiles en `backend/tests/unit/identity/test_business_days.py` (15 días hábiles en Colombia excluyendo sábados, domingos y festivos de `holidays` CO, incluidos los trasladados por la Ley Emiliani; casos que cruzan Semana Santa y fin de año) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Casos con el Día de la Raza, Todos los Santos, Semana
    Santa de 2027, San José y Reyes trasladados; la fecha de la solicitud se toma en Bogotá.
- [x] T153 [P] [US7] Prueba: política de conservación en `backend/tests/unit/identity/test_retention_policy.py` (invitado: fin = mínimo(revocado_en, vence_en), aviso en fin + 60 días y supresión en fin + 90; institucional: aviso en `last_login_at` + 335 días y supresión en + 365; ingresar o renovar mueve las fechas y cancela; el aviso no se repite si `retention_notice_sent_at` existe; FR-034a, FR-034b, FR-034c) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Incluye el aviso de un ciclo anterior (no cuenta) y que la
    supresión no depende de que el aviso haya llegado (FR-034c).
- [x] T154 [P] [US7] Prueba: solicitud en `backend/tests/integration/identity/test_deletion_request_api.py` (`POST /api/v1/me/deletion-request` exige `confirmation` = `ELIMINAR`; responde 202, pasa a `deletion_pending`, incrementa `auth_epoch` y la siguiente petición responde 401; `due_date` a 15 días hábiles; segunda solicitud → 409 `deletion-already-requested`; el último administrador activo recibe 409 `last-admin` y su cuenta no cambia (FR-034d, escenario 7.5); exenta de autorización de datos; audita `deletion.requested`; `GET /api/v1/admin/deletion-requests` con filtro de estado) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). El 409 `deletion-already-requested` se prueba en el servicio:
    tras la primera solicitud el token ya no autentica. La limpieza de `committed_login` borra
    también solicitudes de supresión y eventos del outbox con `user_id`.
- [x] T155 [P] [US7] Prueba: borrado en `backend/tests/integration/identity/test_erase_user.py` (deja la lápida con `status='deleted'` y sin nombre, correo ni `oid`; borra perfil, roles, programas del director, membresías, sesiones, enlaces y correo de invitaciones; conserva `consents` y `audit_events` solo con el UUID; publica `identity.UserErased`; idempotente si se reanuda; tras borrar, ingresar con el mismo `oid` crea una cuenta nueva sin historial (escenario 7.3); revisión automática de que ninguna fila del esquema `identity` contiene el correo o el nombre borrados; FR-033) → Opus
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Revisión automática: ninguna fila de `identity` ni del
    outbox contiene el correo, el nombre o el `oid` borrados. Detectó que la lápida conservaba los
    programas del director (corregido en `User.to_tombstone`, T161).
- [x] T156 [P] [US7] Prueba: tareas programadas en `backend/tests/integration/identity/test_retention_tasks.py` (`process_retention` con `FixedClock`: encola `RetentionNoticeDue` y envía el aviso a Mailpit 30 días antes con la fecha y cómo evitarlo; en la fecha crea la solicitud con origen `guest_retention` o `institutional_retention`; si el correo falla, la supresión sigue; `process_deletion_requests` completa solicitudes y audita `deletion.completed` y `retention.notice_sent`; el último administrador activo con más de 1 año sin ingresar no recibe solicitud de supresión y se audita `retention.skipped_last_admin` (FR-034d); SC-006) → Qwen
  - Terminado: la prueba falla.
  - Estado: implementada por Opus (2026-10-07). Con Mailpit real y reloj fijo; la fecha esperada del aviso
    es la de Bogotá.
- [x] T157 [P] [US7] Pruebas de componente `frontend/src/features/account/DeleteAccountSection.test.tsx` (explica qué se borra y qué se conserva anónimo; exige escribir ELIMINAR; tras confirmar cierra la sesión) y `frontend/src/features/admin/DeletionRequestsPage.test.tsx` (estado y fecha límite) → Qwen
  - Terminado: las pruebas fallan.
  - Estado: implementada por Opus (2026-10-07).

### Implementation for User Story 7

- [x] T158 [P] [US7] Implementar `backend/src/saber_uli/identity/domain/business_days.py` para que pase T152 → Qwen
  - Terminado: T152 en verde.
  - Estado: implementada por Opus (2026-10-07). `holidays` (CO) con caché por año.
- [x] T159 [P] [US7] Implementar `backend/src/saber_uli/identity/domain/retention.py` para que pase T153 → Qwen
  - Terminado: T153 en verde.
  - Estado: implementada por Opus (2026-10-07).
- [x] T160 [US7] Implementar `backend/src/saber_uli/identity/application/deletion.py` y `backend/src/saber_uli/identity/api/deletion_router.py` para que pase T154; agregar `getMyDeletionRequest`, `requestMyDeletion` y `adminListDeletionRequests` a `implemented_operations.py` → Qwen
  - Terminado: T154 y la prueba de contrato en verde.
  - Estado: implementada por Opus (2026-10-07). Contrato sin cambios; las 51 operaciones en verde.
    `ensure_other_admin` pasa a ser pública en `admin_users` para compartir el bloqueo de FR-025
    con la supresión (FR-034d). La solicitud publica `identity.DeletionRequested` por el outbox:
    el worker la procesa en segundos y `process_deletion_requests` queda de respaldo.
- [x] T161 [US7] Implementar `backend/src/saber_uli/identity/application/erase_user.py` para que pase T155 → Opus
  - Terminado: T155 en verde.
  - Estado: implementada por Opus (2026-10-07). `EraseUser` en dos transacciones (`in_progress` y
    `completed`), reanudable. `PersonalDataEraser` borra perfil, membresías, sesiones y el
    contacto y los enlaces de sus invitaciones como invitado; conserva `consents`, auditoría y el
    contenido que la persona creó (grupos, invitaciones enviadas con `invited_by` a la lápida).
- [x] T162 [US7] Implementar `process_retention` y `process_deletion_requests` en `backend/src/saber_uli/identity/infrastructure/tasks.py`, el manejador `backend/src/saber_uli/identity/infrastructure/handlers/retention_notice.py` y las plantillas `backend/src/saber_uli/notifications/infrastructure/templates/retention_notice_{guest,institutional}.{html,txt}.j2` para que pase T156 → Qwen
  - Terminado: T156 en verde.
  - Estado: implementada por Opus (2026-10-07). `apply_retention` (aplicación) decide con los datos
    vigentes de cada cuenta en su propia transacción; `RetentionNoticeHandler` recalcula antes de
    enviar y no envía si la persona ingresó o renovó. `retention_notice_sent_at` se marca al
    encolar el aviso. Nuevo `InvitationRepository.latest_for_guest`.
- [x] T163 [US7] Implementar `frontend/src/features/account/DeleteAccountSection.tsx` y `frontend/src/features/admin/DeletionRequestsPage.tsx` para que pase T157 → Qwen
  - Terminado: T157 en verde.
  - Estado: implementada por Opus (2026-10-07). La sección vive en `/mi-cuenta` (US8 la llevará también a
    `/mi-cuenta/datos`); `/admin/supresiones` con guardia `deletions:read`. `formatDay` muestra
    las fechas sin hora como días de Colombia (con `new Date("2026-10-28")` salía el día
    anterior).
- [x] T164 [US7] Prueba e2e `frontend/tests/e2e/us7-deletion.spec.ts` (V18: solicitud, cierre inmediato, solicitud visible para el administrador, procesamiento por el worker, reingreso como cuenta nueva) → Qwen
  - Terminado: pasa contra el stack `e2e`.
  - Estado: implementada por Opus (2026-10-07). El worker completa la solicitud por el outbox en segundos.
    axe detectó que la tabla de supresiones no era alcanzable con teclado al desplazarse en el
    celular (corregido). En verde 14 de 15 corridas completas con el outbox vacío al empezar.
- [x] T165 [US7] Revisión de US7 (T152–T164) en `specs/001-identidad-acceso/tasks.md`: que no queden datos personales tras la supresión, plazos de la Ley 1581, FR-032 a FR-034c y SC-006 → Opus
  - Terminado: tareas aprobadas y marcadas.
  - Revisión de Opus (2026-10-07): T152–T164 aprobadas.
    - Sin datos personales tras la supresión (FR-033): lápida con `CHECK` en la base y revisión
      automática de todo el esquema `identity` y del outbox (T155). Los registros de la API y del
      worker solo llevan identificadores, orígenes y conteos.
    - Plazos de la Ley 1581 y SC-006: fecha límite de 15 días hábiles con festivos de Colombia; la
      solicitud se procesa en segundos por el outbox y cada 15 minutos como respaldo.
    - FR-032: confirmación escrita, acceso cortado en la misma petición (`auth_epoch` + 1 y
      sesiones revocadas) y reingreso como cuenta nueva (escenario 7.3, V18).
    - FR-034 a FR-034c: listado del administrador con estado y fecha límite; aviso 30 días antes
      con la fecha y cómo evitarlo; ingresar o renovar cancela; la supresión sigue si el correo
      falla. FR-034d: el último administrador recibe 409 y la conservación automática no lo avisa
      ni lo suprime (`retention.skipped_last_admin` una vez por ciclo). FR-034e ya estaba en
      `expire_invitations` (US5).
    - Sin cambios en el contrato, el modelo de datos ni los ADR.
    - Riesgos aceptados: (1) si el aviso falla de forma definitiva no se reintenta en el mismo
      ciclo (`retention_notice_sent_at` se marca al encolar), riesgo ya aceptado en la spec;
      (2) invitaciones posteriores al mismo correo que no quedaron enlazadas al invitado siguen la
      purga de FR-034e, no la supresión.
    - Pendiente para T173: la tabla de `/admin/auditoria` usa el mismo contenedor desplazable sin
      foco que se corrigió en supresiones; revisarla con axe en el celular.
    - Pruebas e2e inestables de historias anteriores, una vez cada una en unas 30 corridas: V5
      (US4) y el último administrador (US6) en corridas seguidas, con el outbox aún enviando los
      200 correos del lote de la corrida anterior; V10 (US5) una vez con el outbox vacío, sin
      capturar el error. Quedan para investigar.

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
