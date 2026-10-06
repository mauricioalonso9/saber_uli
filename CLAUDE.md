# CLAUDE.md

## Proyecto Saber Uli

Saber Uli es un juego tipo Duolingo (PWA instalable en celulares) para que la comunidad de la
Universidad Libre se prepare para los cinco módulos genéricos de las pruebas Saber Pro del ICFES:
Lectura crítica, Razonamiento cuantitativo, Competencias ciudadanas, Comunicación escrita e Inglés.
La metodología es Spec-Driven Development (SDD) con GitHub Spec Kit; el kit de prompts de
referencia está en `docs/SABER_ULI_KIT_SDD.md`.

Decisiones confirmadas:

| Tema | Decisión |
|------|----------|
| Alcance | Solo los 5 módulos genéricos de Saber Pro |
| Acceso | Comunidad Unilibre con SSO de Microsoft 365 (Entra ID/OIDC) + invitados por invitación |
| Banco de preguntas | Banco inicial incluido; la app permite cargar ítems nuevos y actualizar existentes |
| Stack | Sin PHP. Backend Python (FastAPI); frontend React + TypeScript como PWA |
| Arquitectura | Monolito modular con contextos delimitados (DDD) y capas hexagonales |
| Despliegue | Docker (Docker Engine + Compose v2) |
| Base de datos | PostgreSQL 18 |

- El banco inicial de preguntas está en `backend/seeds/banco_inicial_saber_uli.json`
  (43 ítems y 3 consignas, en estado `en_revision`, origen `ia`; un docente debe aprobarlos
  antes de publicarlos).
- El estado del trabajo vive en `specs/<feature-activa>/tasks.md`.

## Trabajo con dos modelos

- **Opus** (`claude`): especifica, planea y revisa. Ejecuta `/speckit.constitution`,
  `/speckit.specify`, `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks` y `/speckit.analyze`,
  y hace la revisión final de las tareas.
- **Qwen** (`claude-qwen`): implementa. Ejecuta `/speckit.implement` sobre las tareas asignadas
  en `specs/<feature-activa>/tasks.md` y marca cada tarea terminada como **"lista para revisión"**;
  no cambia el contrato OpenAPI, el modelo de datos ni los ADR (registra dudas como decisiones
  pendientes).
- Opus revisa las tareas marcadas como "lista para revisión", corrige o devuelve con comentarios
  y cierra las aprobadas.
