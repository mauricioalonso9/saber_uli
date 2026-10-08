# Saber Uli

Saber Uli es un juego al estilo de Duolingo para que la comunidad de la Universidad Libre se
prepare para los cinco módulos genéricos de las pruebas Saber Pro del ICFES: Lectura crítica,
Razonamiento cuantitativo, Competencias ciudadanas, Comunicación escrita e Inglés. Se instala en
el celular como aplicación web progresiva (PWA) y funciona sin conexión hasta 7 días.

La comunidad Unilibre ingresa con su cuenta de Microsoft 365 (Entra ID); las personas externas,
con una invitación por correo.

## Estado

| Funcionalidad | Estado |
|---------------|--------|
| [001 Identidad, acceso institucional e invitados](specs/001-identidad-acceso/spec.md) | En cierre (fase 11) |
| Banco de preguntas, módulos y juego | Por especificar |

El banco inicial de preguntas está en
[`backend/seeds/banco_inicial_saber_uli.json`](backend/seeds/banco_inicial_saber_uli.json): 43
ítems y 3 consignas generados con IA, en estado `en_revision` hasta que un docente los apruebe.

## Tecnología

| Capa | Elección |
|------|----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2 (asyncpg), Alembic, Celery |
| Frontend | React 19 + TypeScript, Vite, TanStack Router y Query, Tailwind, PWA (Workbox) |
| Datos | PostgreSQL 18, Redis |
| Despliegue | Docker Engine + Compose v2, Nginx como proxy |
| Arquitectura | Monolito modular con contextos delimitados (DDD) y capas hexagonales ([ADR 0001](docs/adr/0001-monolito-modular.md)) |

## Levantar el entorno

Requisitos: Docker Desktop (o Docker Engine con Compose v2), Git, [`uv`](https://docs.astral.sh/uv/)
y Node.js 24.

```powershell
copy .env.example .env      # en Linux o macOS: cp .env.example .env
# Editar .env con las credenciales de Entra ID que entrega la oficina de TI
docker compose up --build
```

La app queda en `http://localhost` y Mailpit (correo de desarrollo) en `http://localhost:8025`.

Sin credenciales de Entra ID se puede trabajar con el perfil `e2e`, que levanta un proveedor
OIDC de prueba. La guía completa (registro en Entra ID, primer administrador, carga de
programas, pruebas, escenarios de validación y producción) está en
[`specs/001-identidad-acceso/quickstart.md`](specs/001-identidad-acceso/quickstart.md).

## Estructura

```text
backend/            API FastAPI, worker y beat de Celery (paquete saber_uli)
  src/saber_uli/    contextos: identity, notifications, shared (domain, application, infrastructure, api)
  migrations/       Alembic
  seeds/            política de datos y banco inicial de preguntas
  tests/            unit, integration (Testcontainers), contract (Schemathesis), infra
frontend/           PWA en React + TypeScript
  src/              app (rutas y guardias), features (por pantalla), shared, api (cliente generado con Orval)
  tests/e2e/        Playwright, axe y modo sin conexión
infra/              Nginx, scripts de PostgreSQL e imagen del proveedor OIDC de prueba
docs/               kit SDD y decisiones de arquitectura (adr/)
specs/              especificaciones por funcionalidad (spec, plan, research, data-model, contrato, tareas)
compose*.yaml       Compose base, desarrollo (override) y producción
```

## Pruebas

```powershell
cd backend ; uv run pytest            # unitarias, integración y contrato (requiere Docker)
cd frontend ; npm test                # Vitest
cd frontend ; npx playwright test     # e2e contra el stack con el perfil e2e
```

CI (`.github/workflows/ci.yml`) corre además ruff, mypy, import-linter, ESLint, Lighthouse CI y
Trivy. Los comandos de cada suite están en la sección 4 de quickstart.md.

## Cómo se trabaja: Spec-Driven Development con dos modelos

El proyecto sigue Spec-Driven Development con [GitHub Spec Kit](https://github.com/github/spec-kit).
El kit de prompts de referencia está en [`docs/SABER_ULI_KIT_SDD.md`](docs/SABER_ULI_KIT_SDD.md).

1. **Opus** especifica, planea y revisa: `/speckit.constitution`, `/speckit.specify`,
   `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks` y `/speckit.analyze`.
2. **Qwen** implementa con `/speckit.implement` las tareas asignadas en
   `specs/<funcionalidad>/tasks.md`, una por commit, y las deja como "lista para revisión". No
   cambia el contrato OpenAPI, el modelo de datos ni los ADR: registra sus dudas como
   "Decisión pendiente".
3. **Opus** revisa esas tareas, corrige o devuelve con comentarios, y marca la casilla al
   aprobarlas.

El estado del trabajo vive en `specs/<funcionalidad>/tasks.md`.
