# Saber Uli — Kit de prompts para Spec-Driven Development (v2)

> Juego tipo Duolingo para preparar los **módulos genéricos de Saber Pro**.
> Metodología: **Spec-Driven Development (SDD)** con **GitHub Spec Kit** + **Claude Code**.
> Los puntos marcados con **[SUPUESTO]** deben confirmarse antes de ejecutar el prompt correspondiente.

## Decisiones confirmadas

| Tema | Decisión |
|------|----------|
| Alcance | Solo los 5 módulos genéricos: Lectura crítica, Razonamiento cuantitativo, Competencias ciudadanas, Comunicación escrita e Inglés |
| Acceso | Comunidad Unilibre con su cuenta Microsoft 365 (SSO) + acceso para invitados |
| Banco de preguntas | Se entrega un banco inicial (`banco_inicial_saber_uli.json`); la aplicación permite cargar ítems nuevos y actualizar los existentes |
| Stack | Sin PHP. Backend en Python (FastAPI), frontend React + TypeScript como **PWA instalable en celulares** |
| Despliegue | Docker (Docker Engine + Compose v2) |
| Base de datos | PostgreSQL 18 |

Estructura oficial que la app debe respetar (Guía de orientación Saber Pro 2026-2, ICFES):
Comunicación escrita 1 tarea abierta, Razonamiento cuantitativo 30, Lectura crítica 30,
Competencias ciudadanas 30 e Inglés 45 preguntas; sesión de 4 h 40 min; puntaje de 0 a 300
por módulo y puntaje global = promedio de los cinco.

---

## 0. Cómo usar este kit

En SDD la especificación es la fuente de verdad: **primero se define el qué y el porqué**
(especificación, sin tecnología), **luego el cómo** (plan técnico), **luego las tareas** y
solo al final el código. Si algo cambia, se cambia primero la especificación.

| # | Fase SDD | Comando Spec Kit | Perfil sugerido | Artefacto que produce |
|---|----------|------------------|-----------------|------------------------|
| 1 | Principios | `/speckit.constitution` | `claude` (Opus) | `.specify/memory/constitution.md` |
| 2 | Especificar | `/speckit.specify` | Opus | `specs/NNN-feature/spec.md` |
| 3 | Aclarar | `/speckit.clarify` | Opus | Ambigüedades resueltas en `spec.md` |
| 4 | Planear | `/speckit.plan` | Opus | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 5 | Desglosar | `/speckit.tasks` | Opus | `tasks.md` |
| 6 | Verificar | `/speckit.analyze` | Opus | Reporte de consistencia spec ↔ plan ↔ tareas |
| 7 | Implementar | `/speckit.implement` | `claude-qwen` (Qwen) | Código + pruebas |
| 8 | Revisar | (revisión manual) | Opus | Tareas cerradas, ajustes |

**Regla de oro:** una especificación por funcionalidad (`001-...`, `002-...`). Se recorre
el ciclo 2→8 completo para cada una, en el orden del roadmap (sección 3).

---

## 1. Preparación del entorno (Windows 11, una sola vez)

```powershell
# 1. Docker Desktop (con backend WSL2) y uv (gestor de Python que usa Spec Kit)
winget install --id Docker.DockerDesktop -e
winget install --id astral-sh.uv -e
# Reiniciar sesión de Windows y abrir Docker Desktop una vez

# 2. Instalar el CLI de Spec Kit
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# 3. Crear el proyecto y conectar Spec Kit con Claude Code (scripts en PowerShell)
mkdir E:\saber-uli; cd E:\saber-uli
git init
specify init --here --integration claude --script ps --force
#   Si "specify" no se reconoce: uv tool update-shell, y abre una terminal nueva
specify check

# 4. Copiar el banco inicial al repositorio
mkdir backend\seeds
copy <ruta>\banco_inicial_saber_uli.json backend\seeds\
```

Notas:
- Abre `claude` en la carpeta y escribe `/speckit` para confirmar que aparecen los comandos.
- Si Claude se detiene en un bloque "Extension Hooks", respóndele `continúa` (es un problema
  conocido en Windows).
- Spec Kit mantiene su propio `CLAUDE.md`. Conserva allí la sección "Trabajo con dos modelos"
  de la plantilla anterior y reemplaza la línea `@docs/PLAN.md` por:
  *"El estado del trabajo vive en `specs/<feature-activa>/tasks.md`."*
- **Requisito externo para el SSO:** la oficina de TI de Unilibre debe registrar la aplicación
  en Microsoft Entra ID y entregarte: *Tenant ID*, *Client ID*, *Client Secret* y las URL de
  redirección (`http://localhost/api/auth/microsoft/callback` en desarrollo y la de
  producción). Solicítalo desde ya; suele tardar.

---

## 2. Prompt 1 — Constitución del proyecto

Ejecutar en `claude` (Opus):

```text
/speckit.constitution
Crea la constitución del proyecto "Saber Uli", un aplicativo web gamificado (estilo Duolingo),
instalable como PWA en celulares, para que la comunidad de la Universidad Libre (Colombia) se
prepare para los cinco módulos de competencias genéricas de las pruebas Saber Pro del ICFES.
Redáctala en español, con principios numerados, verificables y con su justificación.
Incluye estos principios:

I. Especificación primero. Ningún código se escribe sin una especificación aprobada en specs/.
   La especificación es la fuente de verdad; todo cambio de comportamiento empieza por ella.
   Las especificaciones describen el qué y el porqué, nunca la tecnología.

II. Arquitectura de monolito modular con contextos delimitados (DDD). Cada contexto tiene capas
    domain / application / infrastructure / api (arquitectura hexagonal). Las dependencias
    apuntan hacia el dominio. Un contexto no accede a las tablas de otro: se comunica mediante
    servicios de aplicación o eventos de dominio. No se introducen microservicios sin un ADR
    que lo justifique con datos.

III. Contrato primero. El contrato OpenAPI 3.1 de cada funcionalidad se define en el plan antes
     de implementar. El cliente del frontend se genera desde el contrato. Los cambios
     incompatibles requieren versionado de la API.

IV. Pruebas primero (TDD, no negociable). Para cada tarea se escriben primero las pruebas que
    fallan. Pirámide: unitarias de dominio, integración con PostgreSQL 18 real (Testcontainers),
    pruebas de contrato contra OpenAPI y extremo a extremo de los flujos críticos.
    Cobertura mínima del 80 % en dominio y aplicación.

V. Protección de datos personales. Cumplimiento de la Ley 1581 de 2012 y sus decretos:
   autorización expresa del titular, finalidad declarada, minimización, derechos de consulta,
   rectificación y supresión, y cero datos personales en logs. Los datos analíticos se
   seudonimizan. Del directorio institucional solo se toman los datos estrictamente necesarios.

VI. Integridad académica y propiedad intelectual. Los ítems son originales y se alinean a la
    estructura publicada por el ICFES (competencias, afirmaciones, evidencias, partes de
    Inglés). No se reproducen preguntas ni cuadernillos del ICFES. Todo ítem pasa por revisión
    humana antes de publicarse, incluidos los generados con IA. Toda estimación de puntaje se
    rotula como "estimación no oficial".

VII. La gamificación sirve al aprendizaje. Cada respuesta muestra retroalimentación
     explicativa. Las mecánicas de juego (XP, rachas, ligas) refuerzan la práctica constante y
     nunca bloquean el acceso al estudio. No se usan patrones oscuros ni compras dentro de la
     aplicación.

VIII. Móvil primero, accesible e inclusivo. La experiencia principal es una PWA instalable que
      funciona en celulares de gama media, tolera conexiones lentas o intermitentes (práctica
      sin conexión con sincronización posterior) y cumple WCAG 2.2 nivel AA. Español de
      Colombia como idioma por defecto.

IX. Seguridad por diseño. Referencia OWASP ASVS nivel 2. Autenticación institucional delegada
    en Microsoft Entra ID (OIDC) y cuentas de invitado con controles propios. Secretos solo por
    variables de entorno, mínimo privilegio, limitación de peticiones, dependencias escaneadas
    en CI.

X. Reproducibilidad y operación (12-factor). Todo el sistema levanta con `docker compose up`.
   Migraciones versionadas, configuración por entorno, health checks, logs estructurados en
   JSON e imágenes que corren sin root.

XI. Simplicidad. YAGNI: se construye lo que la especificación pide. Toda dependencia nueva se
    justifica en research.md y toda decisión arquitectónica relevante se registra como ADR en
    docs/adr/. No se usa PHP en ningún componente.

Gobernanza: la constitución prevalece sobre cualquier otra práctica. Las enmiendas se hacen
por pull request, con versión semántica de la constitución y registro del cambio. /speckit.plan
y /speckit.analyze deben verificar el cumplimiento de cada principio.
```

---

## 3. Roadmap de funcionalidades (orden de especificación)

| Spec | Funcionalidad | Fase |
|------|---------------|------|
| 001 | Identidad: SSO Microsoft 365, invitados, roles, perfil y consentimiento | MVP |
| 002 | Banco de ítems: carga inicial, importación, actualización, versionado y revisión | MVP |
| 003 | Ruta de aprendizaje y sesiones de práctica, PWA con práctica sin conexión | MVP |
| 004 | Gamificación núcleo: XP, rachas, metas diarias, logros | MVP |
| 005 | Motor adaptativo y repaso espaciado | MVP+ |
| 006 | Diagnóstico inicial y simulacros cronometrados con estimación de puntaje | MVP+ |
| 007 | Ligas semanales y tablas de clasificación | v1 |
| 008 | Panel docente / dirección de programa y exportación analítica | v1 |
| 009 | Notificaciones (correo y push PWA) | v1 |
| 010 | Comunicación escrita: textos argumentativos con rúbrica y retroalimentación asistida | v2 |
| 011 | Generación asistida de ítems con IA dentro de la app | v2 |

---

## 4. Prompts de especificación (`/speckit.specify`)

> Sin tecnología: solo usuarios, comportamiento, reglas y criterios de aceptación.
> Después de cada uno, ejecutar `/speckit.clarify` (sección 5).

### 001 — Identidad, acceso institucional e invitados

```text
/speckit.specify
Funcionalidad: identidad, acceso, roles, perfil y consentimiento de datos en Saber Uli.

Contexto: Saber Uli es un juego tipo Duolingo para preparar los cinco módulos genéricos de las
pruebas Saber Pro del ICFES, dirigido a la comunidad de la Universidad Libre, con acceso
limitado para invitados.

Actores: Estudiante Unilibre, Invitado, Docente (crea y revisa contenido, ve el progreso de sus
grupos), Director de programa (ve la analítica del programa) y Administrador (gestiona usuarios,
invitaciones, programas y parámetros).

Historias de usuario:
- Como miembro de la comunidad Unilibre quiero ingresar con mi cuenta institucional de
  Microsoft 365, sin crear otra contraseña.
- En mi primer ingreso quiero que mi perfil se cree automáticamente con mi nombre y correo
  institucional, y completar solo programa académico, semestre, fecha estimada de presentación
  de Saber Pro y meta diaria.
- Como invitado quiero acceder con una invitación enviada a mi correo, sin necesitar una cuenta
  Unilibre [SUPUESTO: invitados por invitación de un administrador o docente, con acceso por
  enlace mágico al correo; sin registro abierto].
- Como administrador quiero enviar invitaciones individuales o por lote, con fecha de
  vencimiento del acceso, y revocarlas.
- Como cualquier usuario quiero aceptar o rechazar de forma explícita la política de
  tratamiento de datos antes de usar la plataforma, y consultar o revocar mi autorización.
- Como usuario quiero solicitar la eliminación de mi cuenta y de mis datos personales.
- Como administrador quiero asignar roles y asociar docentes a grupos o cohortes.

Reglas:
- Solo las cuentas del inquilino Microsoft 365 de Unilibre ingresan como comunidad
  institucional; cualquier otra cuenta Microsoft es rechazada con un mensaje claro.
- Los invitados pueden practicar, hacer simulacros y ganar XP, pero no aparecen en las ligas
  institucionales ni en la analítica del programa, y su acceso vence en la fecha definida.
- Sin autorización de tratamiento de datos no se puede usar la plataforma.
- Un usuario puede tener varios roles. El rol inicial de una cuenta institucional es
  Estudiante; los demás los asigna un administrador.
- Toda acción administrativa sobre usuarios e invitaciones queda auditada.

Criterios de éxito: un estudiante Unilibre entra y empieza su primera lección en menos de
1 minuto; el 100 % de los usuarios activos tiene autorización vigente registrada con fecha y
versión de la política; ningún invitado vencido puede ingresar.

Fuera de alcance: pagos, inicio de sesión con redes sociales, registro abierto al público.
```

### 002 — Banco de ítems: carga inicial, importación y actualización

```text
/speckit.specify
Funcionalidad: banco de ítems alineado a la estructura del ICFES, con carga inicial, importación
masiva, actualización, versionado y flujo de revisión.

Problema: la calidad del aprendizaje depende de preguntas bien construidas, con
retroalimentación y trazables a lo que evalúa el ICFES. El sistema debe arrancar con un banco
inicial y crecer con ítems que carguen y mejoren los docentes.

Estructura del contenido (los módulos y su taxonomía son datos configurables, no valores fijos):
- Lectura crítica, Razonamiento cuantitativo y Competencias ciudadanas: selección múltiple con
  única respuesta y 4 opciones, etiquetadas con competencia, afirmación y evidencia.
  Razonamiento cuantitativo además con componente (estadística, geometría, álgebra y cálculo)
  y tipo de situación. Lectura crítica con tipo de texto (continuo o discontinuo, literario o
  informativo); sus textos tienen máximo 500 palabras.
- Inglés: siete partes con formatos distintos. Parte 1 es de emparejamiento (5 descripciones
  y 8 palabras compartidas); partes 2 a 5 tienen 3 opciones; partes 6 y 7 tienen 4 opciones.
  Por eso el número de opciones de un ítem es variable y las opciones pueden ser compartidas
  por un contexto.
- Comunicación escrita: consignas abiertas para texto argumentativo, asociadas a una rúbrica
  (planteamiento, organización y forma de expresión) y a una condición de pertinencia.
- Varios ítems pueden compartir un contexto (texto, tabla, imagen o lista de opciones).
- Toda opción tiene retroalimentación: la correcta explica por qué lo es; las incorrectas,
  el error que representan. Cada ítem tiene además una explicación general.

Historias de usuario:
- Como administrador quiero cargar el banco inicial incluido en el proyecto
  (backend/seeds/banco_inicial_saber_uli.json) al desplegar por primera vez, sin duplicar
  ítems si la carga se repite.
- Como docente quiero importar ítems nuevos en lote desde un archivo con el mismo formato del
  banco inicial o desde una plantilla de hoja de cálculo, ver una vista previa y un reporte de
  errores por ítem antes de confirmar.
- Como docente quiero actualizar ítems existentes en lote: si el identificador del ítem ya
  existe, el sistema crea una nueva versión en lugar de duplicarlo, y me muestra qué cambió.
- Como docente quiero crear, editar y previsualizar ítems y contextos tal como los verá el
  estudiante en el celular.
- Como docente revisor quiero aprobar, devolver con comentarios o rechazar ítems.
- Como docente quiero exportar el banco (o un filtro de él) en el mismo formato de
  importación.
- Como docente quiero ver la cobertura del banco frente a la distribución del examen (por
  ejemplo, porcentaje de ítems por afirmación en Lectura crítica o por parte en Inglés) para
  saber dónde faltan preguntas.
- Como docente quiero ver las estadísticas de cada ítem publicado (porcentaje de acierto,
  opciones más elegidas y discriminación) para mejorarlo o retirarlo.

Reglas:
- Estados del ítem: Borrador → En revisión → Publicado → Retirado. Solo los publicados llegan a
  los estudiantes. El autor no puede aprobar su propio ítem.
- Los ítems del banco inicial y los generados con IA entran como "En revisión" y marcados con
  su origen.
- Editar o reimportar un ítem publicado crea una nueva versión; las respuestas históricas
  conservan la versión respondida y las estadísticas se reinician por versión.
- Validaciones de importación: exactamente una opción correcta, número de opciones acorde al
  módulo o parte, retroalimentación en todas las opciones, códigos de taxonomía existentes,
  textos de Lectura crítica de máximo 500 palabras y detección de ítems duplicados.
- No se cargan preguntas copiadas de publicaciones del ICFES.

Criterios de éxito: el banco inicial (43 ítems y 3 consignas) se carga sin errores; importar o
actualizar 500 ítems válidos tarda menos de un minuto; una reimportación del mismo archivo no
crea duplicados.
```

### 003 — Ruta de aprendizaje, sesiones de práctica y PWA

```text
/speckit.specify
Funcionalidad: ruta de aprendizaje y sesiones de práctica tipo lección, usables desde el
celular como aplicación instalada, incluso con conexión intermitente.

Experiencia deseada (inspirada en Duolingo): el estudiante ve un camino visual por módulo,
dividido en unidades y lecciones. Cada lección es una sesión corta de 8 a 12 ítems, de 3 a 5
minutos.

Historias de usuario:
- Como estudiante quiero instalar Saber Uli en la pantalla de inicio de mi celular (Android e
  iPhone) y abrirla como una aplicación, sin pasar por una tienda.
- Como estudiante quiero ver mi ruta por módulo, con las lecciones completadas, la actual y las
  siguientes.
- Como estudiante quiero responder un ítem y recibir de inmediato si acerté, la explicación y,
  si fallé, por qué mi opción era incorrecta.
- Como estudiante quiero que los ítems que fallé vuelvan a aparecer al final de la sesión.
- Como estudiante quiero ver un resumen al terminar: aciertos, tiempo, XP ganada y competencias
  practicadas.
- Como estudiante quiero retomar una sesión interrumpida.
- Como estudiante quiero seguir practicando si pierdo la conexión (por ejemplo, en
  TransMilenio): mis respuestas se guardan en el celular y se sincronizan al volver la red.
- Como estudiante quiero practicar libremente un módulo o competencia fuera de la ruta.

Reglas:
- Desbloquear una lección requiere completar la anterior o aprobar una prueba de salto.
- Se registra cada respuesta con la opción elegida, el tiempo, el intento, la versión del ítem
  y si se respondió sin conexión.
- La app descarga por adelantado las próximas lecciones para que estén disponibles sin
  conexión. Las respuestas sincronizadas tarde no se duplican ni duplican recompensas.
- Una lección se completa al responder correctamente todos sus ítems, incluidos los repetidos.

Criterios de éxito: el paso entre ítems se percibe inmediato (menos de 300 ms en el percentil
95); la app puntúa al menos 90 en rendimiento y cumple los criterios de PWA instalable en
Lighthouse; una lección descargada se completa en modo avión y se sincroniza sin pérdidas.
```

### 004 — Gamificación núcleo

```text
/speckit.specify
Funcionalidad: gamificación núcleo (XP, rachas, metas diarias y logros).

Objetivo: fomentar la práctica diaria y constante, que es lo que mejora el desempeño en Saber
Pro, sin bloquear nunca el acceso al estudio.

Historias de usuario:
- Como estudiante quiero ganar XP por cada lección, con bonificaciones por sesiones perfectas y
  por repasar errores.
- Como estudiante quiero mantener una racha de días consecutivos cumpliendo mi meta diaria y
  ver mi racha actual y la máxima.
- Como estudiante quiero tener protectores de racha que se ganan con práctica y cubren un día
  sin estudio.
- Como estudiante quiero elegir mi meta diaria (casual, regular, intensa) y ver mi avance del
  día.
- Como estudiante quiero desbloquear logros (por ejemplo, primera lección, 7 días de racha,
  dominar una competencia) y verlos en mi perfil.
- Como estudiante quiero ver una celebración breve al completar lecciones y metas.

Reglas:
- El día de la racha se calcula en la zona horaria America/Bogota.
- Las lecciones completadas sin conexión cuentan para el día en que se respondieron, no para el
  día en que se sincronizaron.
- Los cálculos de XP, racha y logros son idempotentes: reintentar una petición no duplica
  recompensas.
- Las reglas de puntuación son configurables por un administrador sin desplegar código.
- Sin vidas ni corazones que impidan estudiar.

Criterios de éxito: el 40 % de los estudiantes activos mantiene una racha de 3 o más días al
mes de lanzamiento (meta de producto, medible).
```

### 005 a 011 — Prompts resumidos (se amplían al llegar a cada uno)

```text
/speckit.specify 005: Motor adaptativo y repaso espaciado. El sistema estima el dominio del
estudiante por competencia o afirmación (y por parte en Inglés) y la dificultad real de cada
ítem a partir de las respuestas, y selecciona ítems en la zona de desarrollo (ni muy fáciles ni
muy difíciles). Programa repasos de los ítems y competencias falladas según una curva de
olvido. El estudiante ve su nivel de dominio por competencia. Las reglas son explicables.

/speckit.specify 006: Diagnóstico inicial y simulacros. Al iniciar, una prueba diagnóstica
corta por módulo ubica al estudiante en la ruta. Simulacros cronometrados por módulo y completos
con la estructura oficial (CE 1 tarea, RC 30, LC 30, CC 30, Inglés 45; 4 h 40 min en total),
respetando la distribución aproximada por competencia, afirmación o parte. Estimación de puntaje
en escala 0-300 por módulo y puntaje global (promedio de los cinco), rotulada como no oficial y
comparada con una meta configurable [SUPUESTO: meta institucional de 180 puntos]. Informe de
fortalezas y debilidades por competencia.

/speckit.specify 007: Ligas semanales. Grupos de 20 a 30 estudiantes Unilibre con nivel de
actividad similar compiten por XP semanal. Ascensos y descensos entre divisiones. Tablas por
liga, por programa y por cohorte, con opción de aparecer con alias. Los invitados no
participan.

/speckit.specify 008: Panel docente y dirección de programa. Progreso por estudiante, grupo y
cohorte; mapa de calor de dominio por competencia; estudiantes en riesgo (inactividad o bajo
dominio); ítems con mal desempeño psicométrico; cobertura del banco. Exportación de datos
seudonimizados y vistas de solo lectura para herramientas de inteligencia de negocios como
Power BI. Los invitados se excluyen de la analítica institucional.

/speckit.specify 009: Notificaciones. Recordatorios de racha y meta diaria, aviso de cierre de
liga, resumen semanal. Por correo y notificaciones push de la PWA (en iPhone solo cuando la app
está instalada en la pantalla de inicio), con preferencias por usuario y horarios silenciosos.

/speckit.specify 010: Comunicación escrita. El estudiante redacta un texto argumentativo ante
una consigna, con límite de tiempo y extensión máxima equivalente a dos páginas. Primero se
verifica la pertinencia (toma posición y da razones); luego se evalúa con la rúbrica
(planteamiento, organización, forma de expresión). Retroalimentación preliminar asistida por IA
y calificación final opcional por un docente.

/speckit.specify 011: Generación asistida de ítems. Un docente elige módulo, afirmación o parte,
dificultad y cantidad, y el sistema genera borradores originales con IA en el formato del banco,
con retroalimentación completa. Los borradores entran "En revisión", marcados como generados
por IA, y siguen el flujo normal de aprobación. Se registra el modelo usado y quién aprobó.
```

---

## 5. Prompt — Aclaración (después de cada `/speckit.specify`)

```text
/speckit.clarify
Revisa la especificación activa con foco en: casos límite, reglas de negocio ambiguas, datos
personales involucrados, comportamiento sin conexión o con red lenta, diferencias entre
usuarios institucionales e invitados, permisos por rol y criterios de aceptación que no sean
medibles. Hazme las preguntas de a una y actualiza spec.md con mis respuestas.
```

---

## 6. Prompt — Plan técnico y arquitectura (`/speckit.plan`)

> Se usa completo en la **primera** funcionalidad (001), que además establece la base del
> proyecto. Para las siguientes basta con: `/speckit.plan Usa el stack y la arquitectura
> definidos en specs/001-*/plan.md y en los ADR vigentes.`

```text
/speckit.plan
Genera el plan técnico de esta funcionalidad. Al ser la primera, el plan también establece la
base del proyecto (estructura del repositorio, Docker, CI y convenciones). Verifica cada
decisión contra la constitución. Ningún componente usa PHP.

ARQUITECTURA GENERAL
- Monorepo con monolito modular. Backend y frontend separados, comunicados por una API REST
  definida con OpenAPI 3.1.
- Contextos delimitados del backend: identity, content (banco de ítems), learning (rutas,
  sesiones, motor adaptativo), gamification, assessment (diagnóstico y simulacros), analytics,
  notifications y shared (kernel compartido).
- Cada contexto con capas domain / application / infrastructure / api (hexagonal). Los
  repositorios son puertos en el dominio y adaptadores en la infraestructura.
- Comunicación entre contextos con eventos de dominio (por ejemplo, LeccionCompletada → otorgar
  XP) mediante un bus en proceso y el patrón outbox transaccional para el procesamiento
  asíncrono.

BACKEND
- Python 3.13 o superior, FastAPI, Pydantic v2, SQLAlchemy 2 (asíncrono) con asyncpg, Alembic
  para migraciones.
- Tareas en segundo plano y programadas (cierre de rachas, ligas, notificaciones, procesamiento
  del outbox, importaciones grandes) con Celery y Celery Beat sobre Redis.
- Autenticación institucional: OpenID Connect con Microsoft Entra ID, flujo authorization code
  con PKCE resuelto en el backend (cliente confidencial, librería Authlib o MSAL para Python),
  restringido al tenant de Unilibre mediante validación del claim tid. El frontend nunca ve
  tokens de Microsoft.
- Invitados: invitación con token de un solo uso y enlace mágico enviado por correo, con
  vencimiento y revocación; sin contraseñas almacenadas.
- Sesión propia de la app para ambos tipos de usuario: JWT de acceso de corta duración y
  refresh token rotativo en cookie httpOnly, Secure y SameSite. Autorización por roles y
  permisos.
- Banco de ítems: JSON Schema versionado del formato de intercambio (el de
  backend/seeds/banco_inicial_saber_uli.json), comando CLI idempotente de carga inicial
  ejecutado por el servicio de migraciones, importación y exportación por API (JSON y XLSX),
  upsert por identificador de ítem con creación de nuevas versiones.
- Motor adaptativo (spec 005): calificación tipo Elo por estudiante-afirmación y por ítem para
  el MVP, dejando una interfaz que permita migrar a TRI (teoría de respuesta al ítem) cuando
  haya datos suficientes. Repaso espaciado con FSRS o SM-2; decídelo en research.md.
- API de sincronización para la PWA: recepción de respuestas en lote con claves de
  idempotencia y marca de tiempo del cliente.
- Calidad: ruff, mypy en modo estricto, pytest, pytest-asyncio, Testcontainers con
  postgres:18, Schemathesis para pruebas de contrato.
- Logs JSON con structlog, endpoints /health y /ready, trazas OpenTelemetry opcionales.

FRONTEND (PWA)
- React con TypeScript y Vite, mobile-first.
- PWA con vite-plugin-pwa y Workbox: manifest con íconos y pantalla de inicio, instalación en
  Android y iOS (incluye guía de "Agregar a pantalla de inicio" para iPhone), service worker
  con precarga del shell de la app y caché de lecciones descargadas.
- Práctica sin conexión: lecciones y respuestas pendientes en IndexedDB (Dexie), cola de
  sincronización con reintentos e idempotencia, indicador visible de estado de conexión.
- Notificaciones push con Web Push y claves VAPID (spec 009).
- Enrutamiento y datos: TanStack Router y TanStack Query. Estado de UI con Zustand.
- Interfaz: Tailwind CSS y componentes shadcn/ui, animaciones con Motion para la experiencia de
  juego. Formularios con react-hook-form y zod.
- Cliente de API generado automáticamente desde el OpenAPI (orval), sin escribir llamadas a
  mano.
- Organización por funcionalidades: src/features/<feature>, src/shared, src/api (generado).
- Pruebas: Vitest con Testing Library, MSW para simular la API y Playwright para los flujos de
  extremo a extremo (incluido modo sin conexión y viewport móvil). Lighthouse CI para
  rendimiento y criterios PWA.
- Accesibilidad WCAG 2.2 AA verificada con axe en CI. Textos en español de Colombia con i18n
  preparado.

BASE DE DATOS: PostgreSQL 18
- Imagen oficial postgres:18. IMPORTANTE: desde la versión 18 el volumen se monta en
  /var/lib/postgresql (no en /var/lib/postgresql/data).
- Claves primarias con uuidv7() nativo de PostgreSQL 18 (ordenables en el tiempo). Los ítems
  conservan además su identificador de negocio (por ejemplo, LC-0001) como clave única.
- Un esquema por contexto delimitado (identity, content, learning, gamification, assessment,
  analytics). Usuarios de base de datos con mínimo privilegio por servicio.
- JSONB para el contenido enriquecido de ítems y contextos; tabla de versiones de ítems;
  restricciones CHECK, FK e índices explícitos; tabla outbox; auditoría.
- Esquema analytics con vistas de solo lectura y un rol dedicado para conectar herramientas de
  inteligencia de negocios.
- Extensión pg_stat_statements activa.

DOCKER
- compose.yaml con los servicios: proxy (Nginx: sirve el frontend compilado con las cabeceras
  correctas para el service worker y hace de proxy inverso hacia /api), api, worker, beat,
  migrate (una sola ejecución: migraciones + carga idempotente del banco inicial), db
  (postgres:18), redis y, solo en desarrollo, mailpit para los correos de invitación.
- compose.override.yaml para desarrollo con recarga en caliente; compose.prod.yaml para
  producción con HTTPS (requisito para PWA y push fuera de localhost).
- Dockerfiles multi-etapa, usuario no root, health checks en todos los servicios,
  depends_on con condition: service_healthy, .env.example documentado (incluye variables de
  Entra ID y VAPID) y sin secretos en el repositorio.

ESTRUCTURA DEL REPOSITORIO
saber-uli/
├── .specify/ y specs/            # artefactos SDD
├── backend/
│   ├── src/saber_uli/<contexto>/{domain,application,infrastructure,api}/
│   ├── migrations/
│   ├── seeds/banco_inicial_saber_uli.json
│   ├── schemas/banco_items.schema.json
│   └── tests/{unit,integration,contract}/
├── frontend/
│   ├── src/{app,features,shared,api}/
│   ├── public/ (manifest e íconos PWA)
│   └── tests/e2e/
├── infra/{nginx,docker,postgres}/
├── docs/adr/
├── compose.yaml, compose.override.yaml, compose.prod.yaml
└── .github/workflows/            # CI: lint, tipos, pruebas, Lighthouse, build, escaneo Trivy

CONVENCIONES
- Conventional Commits, ramas por funcionalidad (las crea Spec Kit), pre-commit con linters.
- Código en inglés; textos de interfaz, documentación y ADR en español.

ENTREGABLES DEL PLAN
- research.md: alternativas evaluadas y justificación de cada dependencia.
- data-model.md: entidades, relaciones, estados e invariantes del dominio.
- contracts/openapi.yaml: endpoints, esquemas, errores con RFC 9457 (Problem Details) y
  paginación.
- quickstart.md: cómo levantar el entorno en Windows con Docker Desktop y en un servidor con
  Docker Engine, incluido el registro de la app en Entra ID.
- ADR iniciales: monolito modular, FastAPI, PostgreSQL 18 con uuidv7, outbox, autenticación
  Entra ID + invitados, PWA sin conexión y estrategia del motor adaptativo.
```

---

## 7. Prompts — Tareas, análisis e implementación

### Tareas (Opus)

```text
/speckit.tasks
Genera las tareas ordenadas por dependencias y agrupadas por historia de usuario, de modo que
cada historia sea entregable e independiente. Para cada tarea, primero la prueba que falla y
luego la implementación (TDD). Marca con [P] las tareas paralelizables. Indica en cada tarea
los archivos que toca y su criterio de terminado. Asigna a Qwen las tareas de implementación
bien definidas y deja para Opus las de diseño, seguridad y revisión.
```

### Análisis de consistencia (Opus)

```text
/speckit.analyze
Verifica la consistencia entre constitución, spec.md, plan.md, data-model.md, el contrato
OpenAPI y tasks.md. Reporta requisitos sin tarea, tareas sin requisito, violaciones a la
constitución y criterios de aceptación sin prueba asociada. No modifiques archivos: solo
reporta y propone correcciones.
```

### Implementación (Qwen)

```text
/speckit.implement
Implementa las tareas pendientes asignadas a Qwen de specs/<feature-activa>/tasks.md, en orden.
Reglas: escribe primero la prueba y confirma que falla; implementa lo mínimo para que pase;
ejecuta la suite completa del contexto afectado; no cambies el contrato OpenAPI, el modelo de
datos ni decisiones de los ADR (si algo no encaja, regístralo como decisión pendiente y sigue
con lo demás). Marca cada tarea como "lista para revisión" y haz un commit por tarea.
```

### Revisión (Opus)

```text
Revisa las tareas marcadas como "lista para revisión" de specs/<feature-activa>/tasks.md:
cumplimiento de la especificación y de la constitución, calidad del código, pruebas
significativas (no triviales), seguridad y manejo de datos personales. Corrige o devuelve con
comentarios, resuelve las decisiones pendientes y cierra las tareas aprobadas.
```

---

## 8. Banco de preguntas

### 8.1 Banco inicial incluido

`banco_inicial_saber_uli.json` contiene ítems originales de práctica, todos en estado
`en_revision` y con origen `ia`:

| Módulo | Contenido |
|--------|-----------|
| Lectura crítica | 8 ítems sobre 3 textos (columna de opinión, microcuento y reglamento en tabla) |
| Razonamiento cuantitativo | 8 ítems de las 3 competencias, con estadística, geometría y álgebra |
| Competencias ciudadanas | 8 ítems de las 4 competencias |
| Inglés | 19 ítems de las 7 partes (incluye un emparejamiento de la Parte 1) |
| Comunicación escrita | 3 consignas argumentativas + 1 rúbrica de práctica |

El archivo incluye además la taxonomía (competencias, afirmaciones y evidencias parafraseadas
de la guía del ICFES 2026-2), los pesos aproximados por competencia y parte, y la estructura del
examen. **Antes de publicar, un docente de cada área debe revisar y aprobar los ítems.**

### 8.2 Prompt para ampliar el banco (Opus genera, docentes revisan)

Ejecutar por lotes pequeños (10 a 15 ítems), en `claude` dentro del repositorio:

```text
Lee backend/seeds/banco_inicial_saber_uli.json: su taxonomía, sus pesos y sus ítems son el
estándar de formato y de calidad. Genera [N] ítems nuevos y originales del módulo [MÓDULO],
[afirmación / competencia / parte], dificultad [baja | media | alta], en el mismo formato, y
guárdalos en backend/seeds/lotes/[MÓDULO]-[fecha].json.

Requisitos:
- Originales: no reproduzcas ni parafrasees preguntas del ICFES ni de otros bancos.
- Contextos colombianos y cotidianos, sin estereotipos ni sesgos de género, región o etnia.
- Una sola respuesta correcta, distractores plausibles basados en errores frecuentes reales y
  retroalimentación específica en cada opción.
- Lectura crítica: textos propios de máximo 500 palabras, respetando la proporción de tipos de
  texto. Inglés: el número de opciones que corresponde a cada parte.
- Razonamiento cuantitativo: verifica cada cálculo dos veces y muestra el procedimiento en la
  explicación.
- Identificadores consecutivos a partir del último existente; origen "ia", estado
  "en_revision".
Al terminar, valida el archivo con backend/schemas/banco_items.schema.json y lista los ítems
con su clave correcta para facilitar la revisión docente.
```

Metas sugeridas para un banco que soporte simulacros sin repetir ítems con frecuencia:
unos 150 ítems por módulo de selección múltiple, 225 en Inglés (5 por cada pregunta del examen,
respetando los pesos por parte) y 20 consignas de escritura.

---

## 9. Definición de Terminado (para cada funcionalidad)

- [ ] Todos los criterios de aceptación de spec.md tienen al menos una prueba automatizada.
- [ ] Suites de unitarias, integración, contrato y e2e en verde; cobertura ≥ 80 % en dominio.
- [ ] El contrato OpenAPI coincide con la implementación (Schemathesis sin fallos).
- [ ] `docker compose up` levanta todo desde cero, carga el banco inicial y el quickstart
      funciona.
- [ ] La PWA se instala y la funcionalidad se usa correctamente en un viewport móvil.
- [ ] Sin hallazgos críticos en lint, tipos, accesibilidad (axe), Lighthouse ni escaneo de
      seguridad.
- [ ] ADR y documentación actualizados; `/speckit.analyze` sin inconsistencias abiertas.
- [ ] Revisión de Opus aprobada y rama integrada.
