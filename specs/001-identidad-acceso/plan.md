# Implementation Plan: Identidad, acceso institucional e invitados

**Branch**: `001-identidad-acceso` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-identidad-acceso/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

La funcionalidad 001 define quién entra a Saber Uli, con qué identidad, con qué permisos y bajo
qué autorización de tratamiento de datos. Los miembros de Unilibre ingresan con Microsoft
Entra ID (OIDC, *authorization code* + PKCE resuelto en el backend y restringido al inquilino
por `tid`). Los invitados entran por enlaces de un solo uso enviados al correo, sin contraseñas.
Ambos reciben una sesión propia: JWT de acceso de 10 minutos y token de renovación rotativo en
cookie `HttpOnly`, con 7 días de uso sin conexión (FR-038) y revocación inmediata con conexión.
Se agregan roles combinables, grupos, autorización versionada (Ley 1581), derechos del titular,
supresión manual y automática con avisos, y auditoría inmodificable.

Por ser la primera funcionalidad, el plan también establece la base del proyecto: monorepo con
monolito modular (FastAPI + PostgreSQL 18) y PWA (React + TypeScript), Docker Compose, CI y
convenciones. El detalle de cada decisión está en [research.md](./research.md) y en los ADR
0001–0007 de `docs/adr/`.

## Technical Context

**Language/Version**: Python 3.13 (backend); TypeScript 5 sobre Node.js 24 LTS (frontend)

**Primary Dependencies**:
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2 (asíncrono) + asyncpg, Alembic, Authlib (OIDC),
  PyJWT, Celery + Celery Beat, redis-py, structlog, limits, holidays, Jinja2, OpenTelemetry
  (opcional, desactivado por defecto)
- Frontend: React, Vite, vite-plugin-pwa (Workbox), TanStack Router, TanStack Query, Zustand,
  Tailwind CSS + shadcn/ui, Motion, react-hook-form + zod, orval, Dexie, i18next + react-i18next

**Storage**: PostgreSQL 18 (esquemas `identity` y `shared`; claves `uuidv7()`; extensiones
`citext` y `pg_stat_statements`). Redis 8 (broker de Celery, caché de `auth_epoch`, contadores de
limitación). IndexedDB en el cliente (instantánea de la cuenta para uso sin conexión).

**Testing**: pytest, pytest-asyncio, Testcontainers (`postgres:18`, `redis:8`), respx
(proveedor OIDC simulado), Schemathesis (contrato), import-linter (límites entre contextos),
Vitest + Testing Library + MSW, Playwright + `@axe-core/playwright` (con `mock-oauth2-server`
y Mailpit), Lighthouse CI

**Target Platform**: servidor Linux con Docker Engine + Compose v2 (producción); Windows 11 con
Docker Desktop/WSL2 (desarrollo). Cliente: navegadores móviles modernos (Chrome Android y
Safari iOS 16.4+) como PWA instalada, y navegadores de escritorio.

**Project Type**: aplicación web (API REST + PWA) en monorepo

**Performance Goals**: p95 < 300 ms en endpoints propios (sin contar el tiempo de Microsoft);
validación de un lote de 500 invitaciones < 2 s; correos encolados enviados en < 1 minuto;
primer ingreso completo < 1 minuto (SC-001)

**Constraints**: uso sin conexión hasta 7 días (FR-038); revocación efectiva en la siguiente
petición con conexión; cero datos personales en registros; ASVS nivel 2 en funciones
privilegiadas; WCAG 2.2 AA; HTTPS obligatorio fuera de `localhost`; imágenes sin root

**Scale/Scope**: hasta 40 000 usuarios registrados, 2 000 concurrentes en pico, < 2 000
invitados activos; 8 historias de usuario, 55 operaciones de API en 44 rutas (contrato al
2026-10-08), ~16 pantallas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principio | Cómo lo cumple este plan | Pre | Post |
|---|-----------|--------------------------|-----|------|
| I | Especificación primero | `spec.md` aclarada (5 decisiones registradas); el plan no agrega comportamiento que no esté en la spec | ✅ | ✅ |
| II | Monolito modular DDD | Contextos `identity`, `notifications`, `shared` con capas hexagonales; esquema por contexto; comunicación por fachada o eventos; `import-linter` en CI (R-03, R-04, ADR 0001) | ✅ | ✅ |
| III | Contrato primero | `contracts/openapi.yaml` (OpenAPI 3.1, validado) antes de implementar; cliente con `orval`; Schemathesis en CI; versión `/api/v1` (ADR 0002) | ✅ | ✅ |
| IV | Pruebas primero (TDD) | Pirámide completa con Postgres 18 real y Entra ID simulado; cobertura ≥ 80 % en `domain` y `application` como puerta de CI; la infraestructura ejecutable también tiene pruebas previas (`backend/tests/infra/`) según la constitución 1.0.1 (R-36) | ✅ | ✅ |
| V | Protección de datos | Autorización explícita y versionada; minimización (`openid profile email`, sin Graph); exportación y supresión; conservación automática; procesador de logs sin datos personales; director solo con datos agregados (R-12, R-23–R-27) | ✅ | ✅ |
| VI | Integridad académica | No aplica a esta funcionalidad (no maneja ítems ni puntajes) | N/A | N/A |
| VII | Gamificación al servicio del aprendizaje | Ninguna regla de acceso depende de mecánicas de juego; la meta diaria solo se registra (su efecto es de la spec 004) | ✅ | ✅ |
| VIII | Móvil primero, accesible | PWA con shell sin conexión y 7 días de gracia; axe y Lighthouse en CI; es-CO por defecto con i18n (R-17, R-34, ADR 0006) | ✅ | ✅ |
| IX | Seguridad por diseño | Entra ID con validación de `tid`; tokens con hash y un solo uso; rotación con detección de reutilización; ASVS 3.3.2 en funciones privilegiadas; limitación de peticiones; roles de BD de mínimo privilegio; Trivy en CI; secretos solo por entorno (R-10–R-19, R-31) | ⚠️ | ✅ con justificación |
| X | Reproducibilidad (12-factor) | `docker compose up` levanta todo; migraciones Alembic; configuración por entorno; *health checks*; logs JSON; imágenes sin root (R-09, R-32, R-33) | ✅ | ✅ |
| XI | Simplicidad | Solo se crean los contextos necesarios; permisos en código; CSV en lugar de XLSX; cada dependencia nueva justificada en research.md; 7 ADR; sin PHP | ✅ | ✅ |

**Resultado**: la puerta pasa. La única tensión (IX frente a FR-038, por la duración de las
sesiones) se resolvió en el diseño con sesiones privilegiadas acotadas (R-15) y queda registrada
en *Complexity Tracking*.

## Project Structure

### Documentation (this feature)

```text
specs/001-identidad-acceso/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y justificación de dependencias
├── data-model.md        # Fase 1: entidades, tablas, estados e invariantes
├── quickstart.md        # Fase 1: cómo levantar y validar de punta a punta
├── contracts/
│   └── openapi.yaml     # Fase 1: contrato OpenAPI 3.1
├── checklists/
│   └── requirements.md  # Lista de calidad de la especificación
└── tasks.md             # Fase 2 (/speckit-tasks; no lo crea este comando)
```

### Source Code (repository root)

```text
saber-uli/
├── .specify/  specs/                       # artefactos SDD
├── .github/
│   ├── workflows/ci.yml                    # quality, tests, contract, e2e, lighthouse, build, Trivy
│   └── dependabot.yml
├── backend/
│   ├── pyproject.toml  uv.lock  .importlinter
│   ├── Dockerfile                          # multi-etapa, usuario no root
│   ├── src/saber_uli/
│   │   ├── main.py                         # app FastAPI: routers, middlewares, problem handlers
│   │   ├── cli.py                          # `saber-uli` (grant-admin, migrate, seed)
│   │   ├── worker.py                       # app Celery + programación de Beat
│   │   ├── config.py                       # configuración por entorno
│   │   ├── shared/
│   │   │   ├── domain/                     # Entity, DomainEvent, Clock, errores base
│   │   │   ├── application/                # UnitOfWork, EventBus en proceso
│   │   │   ├── infrastructure/             # db (engine, sesión), outbox, redis, logging, rate limit
│   │   │   └── api/                        # problem details, paginación, dependencias de auth
│   │   ├── identity/
│   │   │   ├── domain/                     # User, Invitation, Consent, Group, Program, permisos,
│   │   │   │                               # reglas de conservación y días hábiles, eventos
│   │   │   ├── application/                # casos de uso (comandos/consultas) y fachada pública
│   │   │   ├── infrastructure/             # repositorios SQLAlchemy, Entra ID (Authlib),
│   │   │   │                               # emisor de tokens, manejadores del outbox, tareas Celery
│   │   │   └── api/                        # routers /api/auth y /api/v1 de identidad
│   │   └── notifications/
│   │       ├── domain/                     # EmailMessage
│   │       ├── application/                # puerto EmailSender, servicio de envío
│   │       ├── infrastructure/             # adaptador SMTP, plantillas Jinja2 (es-CO)
│   │       └── api/                        # (vacío en 001)
│   ├── migrations/                         # Alembic (esquemas identity y shared, roles, grants)
│   ├── seeds/
│   │   ├── banco_inicial_saber_uli.json    # ya existe; se carga en la spec 002
│   │   └── politica_tratamiento_datos_v1.md
│   └── tests/
│       ├── unit/identity/  unit/shared/
│       ├── integration/identity/  integration/shared/
│       ├── contract/
│       └── infra/                          # pruebas de contenedores, Nginx y Compose
├── frontend/
│   ├── package.json  package-lock.json  vite.config.ts  orval.config.ts
│   ├── Dockerfile                          # compila y entrega el estático al proxy
│   ├── public/                             # manifest, íconos PWA
│   ├── src/
│   │   ├── app/                            # router, proveedores, shell, service worker
│   │   ├── api/                            # cliente generado por orval (no se edita a mano)
│   │   ├── features/
│   │   │   ├── auth/                       # /ingresar, /acceso, sesión en memoria, revalidación
│   │   │   ├── onboarding/                 # /bienvenida/datos, /bienvenida/perfil
│   │   │   ├── account/                    # /mi-cuenta, datos, autorización, supresión
│   │   │   ├── invitations/                # /invitaciones (docente y administrador)
│   │   │   ├── teacher/                    # /grupos
│   │   │   └── admin/                      # usuarios, grupos, programas, supresiones,
│   │   │                                   # política, parámetros, auditoría
│   │   └── shared/                         # UI (shadcn/ui), i18n es-CO, Dexie, utilidades
│   └── tests/
│       ├── unit/
│       └── e2e/                            # Playwright (móvil, sin conexión, axe)
├── infra/
│   ├── nginx/                              # configuración del proxy y cabeceras de seguridad
│   ├── docker/                             # mock-oauth2-server (perfil e2e)
│   └── postgres/init/                      # roles y extensiones
├── docs/adr/                               # 0001–0007
├── compose.yaml                            # proxy, api, worker, beat, migrate, db, redis
├── compose.override.yaml                   # desarrollo: recarga en caliente, mailpit
├── compose.prod.yaml                       # producción: TLS, HSTS, SMTP real
├── .env.example                            # incluye Entra ID, JWT, SMTP y (para 009) VAPID
└── .pre-commit-config.yaml
```

**Structure Decision**: aplicación web en monorepo con `backend/` (monolito modular por
contextos con capas hexagonales) y `frontend/` (PWA organizada por funcionalidades). En 001 solo
se crean los contextos `shared`, `identity` y `notifications`; cada especificación posterior
agrega su contexto. El servicio `migrate` de Compose ejecuta Alembic y la carga de la política
v1; la carga idempotente del banco inicial se suma en la spec 002.

### Servicios de Docker Compose

| Servicio | Imagen / build | Rol | Health check |
|----------|----------------|-----|--------------|
| `proxy` | `nginx` + estático del frontend | Sirve la PWA y redirige `/api/` a `api` | `GET /` |
| `api` | `backend/Dockerfile` (Uvicorn) | API REST | `GET /api/health` |
| `worker` | `backend/Dockerfile` (Celery) | Outbox, correo, supresiones | `celery inspect ping` |
| `beat` | `backend/Dockerfile` (Celery Beat) | Tareas programadas | archivo de latido |
| `migrate` | `backend/Dockerfile` (una ejecución) | Alembic + semillas | código de salida |
| `db` | `postgres:18` (volumen en `/var/lib/postgresql`) | Base de datos | `pg_isready` |
| `redis` | `redis:8-alpine` | Broker, caché, límites | `redis-cli ping` |
| `mailpit` | `axllent/mailpit` (solo desarrollo y e2e) | Correo de prueba | `GET /livez` |
| `oidc` | `ghcr.io/navikt/mock-oauth2-server` (solo perfil `e2e`) | Entra ID simulado | `GET /.well-known/…` |

`api`, `worker` y `beat` dependen de `migrate` con
`condition: service_completed_successfully` y de `db` y `redis` con
`condition: service_healthy`.

**Sin root (principio X)**: la regla se verifica sobre el proceso principal de cada servicio.
Las imágenes propias corren con UID 10001 (backend) y como usuario de `nginx-unprivileged`
(proxy). `db` y `redis` usan imágenes oficiales cuyo entrypoint arranca como root solo para
preparar el volumen y luego ejecuta el servidor con un usuario sin privilegios. `mailpit` y
`oidc` se fijan con `user:` en Compose. La prueba de infraestructura
`backend/tests/infra/test_containers.py` comprueba con `docker compose top` que ningún proceso
principal corre con UID 0 (research R-32).

**Datos de arranque**: `migrate` carga la política v1 y los parámetros por defecto. Los programas
académicos se cargan con `saber-uli identity import-programs --csv <archivo>`, de modo que el MVP
(US1–US3) es usable sin la administración de US6.

### Mapa de historias de usuario a componentes

| Historia | Backend (`identity`) | Frontend | Contrato |
|----------|----------------------|----------|----------|
| HU1 Ingreso institucional | `AuthenticateInstitutionalUser`, adaptador Entra ID | `features/auth` | `/api/auth/microsoft/*`, `/api/auth/refresh`, `/api/auth/logout` |
| HU2 Autorización de datos | `DecideConsent`, `RevokeConsent`, `PublishPolicyVersion`, guardia de consentimiento | `features/onboarding`, `features/account` | `/api/v1/me/consents*`, `/api/v1/privacy-policy/*` |
| HU3 Perfil | `UpdateProfile` | `features/onboarding` | `/api/v1/me/profile`, `/api/v1/programs` |
| HU4 Acceso de invitados | `CreateGuestSession`, `RequestSignInLink`, manejadores del outbox | `features/auth` (`/acceso`) | `/api/auth/guest/*` |
| HU5 Gestión de invitaciones | `CreateInvitation`, `ValidateBatch`, `ConfirmBatch`, `ChangeExpiry`, `Revoke`, `Resend` | `features/invitations` | `/api/v1/invitations*`, `/api/v1/invitation-batches*` |
| HU6 Roles y grupos | `SetUserRoles`, `ChangeUserStatus`, casos de grupos y programas | `features/admin`, `features/teacher` | `/api/v1/admin/users*`, `/api/v1/admin/groups*`, `/api/v1/teacher/*` |
| HU7 Supresión | `RequestDeletion`, `EraseUser`, tarea `process_retention` | `features/account`, `features/admin` | `/api/v1/me/deletion-request`, `/api/v1/admin/deletion-requests` |
| HU8 Consulta de datos | `ExportPersonalData` | `features/account` | `/api/v1/me/data-export` |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Sesiones de aprendizaje de 7 días de inactividad y 30 absolutos, por encima del límite de ASVS 4.0.3 V3.3.2 nivel 2 (12 h / 30 min) que pide el principio IX | FR-038 exige 7 días de uso sin conexión; un invitado tendría que pedir un enlace por correo cada 12 horas | Aplicar 12 h / 30 min a todos incumple la especificación. Se acota la desviación: toda función privilegiada (docente, director, administrador) sí exige reautenticación cada 12 h o tras 30 min de inactividad (R-15) |
| Dos niveles de sesión (aprendizaje y privilegiada) en lugar de uno | Es la forma de cumplir a la vez FR-038 y ASVS nivel 2 | Un solo nivel obliga a sacrificar uno de los dos requisitos |
| Celery, Beat y Redis desde la primera funcionalidad | Correos de invitación confiables (outbox) y conservación automática programada (FR-034a/b/c) | Enviar correo dentro de la petición pierde mensajes si el SMTP falla; un cron externo rompe el principio X |

## Riesgos y dependencias externas

| Riesgo o dependencia | Impacto | Mitigación |
|----------------------|---------|------------|
| Registro de la aplicación en Entra ID por TI (Tenant ID, Client ID, secreto, URL de retorno) | Bloquea el ingreso institucional real | Desarrollo y CI con `mock-oauth2-server`; solicitar el registro ya (quickstart §2) |
| Texto definitivo de la política de tratamiento de datos | Sin él no se puede salir a producción | La semilla v1 es un borrador marcado; publicar la versión aprobada por la oficina jurídica con `publishPolicyVersion` |
| Servidor SMTP de producción | Sin él no hay invitados ni avisos de supresión | Mailpit en desarrollo; configuración SMTP por entorno |
| Plazo máximo de 180 días para invitaciones de docentes | Supuesto sin confirmar | Es un parámetro editable (`teacher_max_access_days`) |
| La supresión anual afecta también a estudiantes matriculados que no ingresan en un año (FR-034b) | Pérdida de progreso no esperada | Aviso por correo 30 días antes (FR-034c); revisar con la universidad si se desea otra regla |

## Notas de ejecución

- El script de Spec Kit reporta la rama `001-identidad-acceso`, pero el repositorio sigue en
  `master` y sin commits. Antes de `/speckit-implement` conviene crear la rama de la
  funcionalidad.
- Siguiente paso: `/speckit-tasks` (prompt de la sección 7 del kit).
