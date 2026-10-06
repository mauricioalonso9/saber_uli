# Research: Identidad, acceso institucional e invitados

**Feature**: `001-identidad-acceso` | **Fecha**: 2026-10-05 | **Plan**: [plan.md](./plan.md)

Este documento resuelve las incógnitas técnicas del plan y justifica cada dependencia nueva
(principio XI). Por ser la primera funcionalidad, también fija decisiones de base del proyecto.
Las decisiones de arquitectura relevantes se registran además como ADR en `docs/adr/`.

Formato de cada entrada: **Decisión**, **Justificación**, **Alternativas consideradas**.

---

## A. Base del proyecto

### R-01. Versiones de lenguaje y entorno de ejecución

- **Decisión**: Python 3.13 (imagen `python:3.13-slim`) para el backend; Node.js 24 LTS para
  compilar el frontend; PostgreSQL 18 (`postgres:18`); Redis 8 (`redis:8-alpine`).
- **Justificación**: 3.13 cumple el mínimo del kit y tiene soporte maduro en todas las
  dependencias elegidas (Celery, asyncpg, SQLAlchemy, Testcontainers). Node 24 es la LTS activa.
- **Alternativas**: Python 3.14 (se evaluará cuando Celery y asyncpg publiquen ruedas estables
  para 3.14 en todas las plataformas; el cambio es una línea en el Dockerfile).

### R-02. Gestión de dependencias y herramientas de calidad

- **Decisión**: `uv` para Python (`pyproject.toml` + `uv.lock`); `npm` con `package-lock.json`
  para el frontend; `pre-commit` con ruff, mypy, eslint, prettier y verificación de Conventional
  Commits (`commitizen`).
- **Justificación**: `uv` ya es requisito del entorno (Spec Kit) y es el gestor más rápido con
  lockfile reproducible. `npm` evita agregar otro gestor (pnpm) sin necesidad (YAGNI).
- **Alternativas**: Poetry (más lento, sin ventaja aquí); pnpm (ahorro de disco irrelevante para
  un solo paquete frontend).

### R-03. Monolito modular y contextos creados en esta funcionalidad

- **Decisión**: el backend es un único paquete `saber_uli` con un subpaquete por contexto
  delimitado. En 001 se crean solo `shared` (kernel compartido), `identity` y `notifications`
  (envío de correo). Los contextos `content`, `learning`, `gamification`, `assessment` y
  `analytics` los crea su propia especificación.
- **Justificación**: principio II (DDD hexagonal) y principio XI (YAGNI). Crear carpetas vacías
  no aporta valor ni pruebas.
- **Alternativas**: crear todos los contextos de una vez (código muerto sin especificación).
- **ADR**: [0001-monolito-modular](../../docs/adr/0001-monolito-modular.md).

### R-04. Reglas de dependencia entre capas y contextos

- **Decisión**: dentro de cada contexto, `api → application → domain` e
  `infrastructure → application/domain`; `domain` no importa nada de FastAPI, SQLAlchemy ni
  Pydantic. Entre contextos solo se permite importar el módulo `application` público del otro
  contexto (fachada) o reaccionar a sus eventos. Se verifica en CI con `import-linter`.
- **Justificación**: hace comprobable el principio II en cada pull request.
- **Alternativas**: revisión manual (no verificable de forma automática).
- **Dependencia nueva**: `import-linter` (solo desarrollo).

### R-05. Framework web y validación

- **Decisión**: FastAPI + Pydantic v2; el contrato `contracts/openapi.yaml` es la fuente de
  verdad y la implementación se valida contra él con Schemathesis (principio III).
- **Justificación**: definido en el kit; soporte nativo de OpenAPI 3.1 y asincronía.
- **Alternativas**: Litestar (comunidad más pequeña); Django REST (modelo síncrono y ORM propio).
- **ADR**: [0002-fastapi](../../docs/adr/0002-fastapi.md).

### R-06. Persistencia

- **Decisión**: SQLAlchemy 2 asíncrono + asyncpg; Alembic con un único historial de migraciones
  que crea un esquema por contexto (`identity`, `shared`; los demás llegan con su spec). Claves
  primarias `uuid` con `DEFAULT uuidv7()` nativo de PostgreSQL 18. Volumen de datos montado en
  `/var/lib/postgresql`.
- **Justificación**: definido en el kit. `uuidv7()` da claves ordenables en el tiempo sin
  extensiones y sin generar UUID en la aplicación.
- **Alternativas**: un historial Alembic por contexto (complica el orden de despliegue sin
  beneficio en un monolito).
- **ADR**: [0003-postgresql-18-uuidv7](../../docs/adr/0003-postgresql-18-uuidv7.md).

### R-07. Roles de base de datos (mínimo privilegio)

- **Decisión**: cuatro roles creados por `infra/postgres/init/`:
  `saber_migrator` (DDL, solo lo usa el servicio `migrate`), `saber_app` (DML para `api`,
  `worker` y `beat`), `saber_bi` (solo lectura del esquema `analytics`, se usará en 008) y el
  superusuario de la imagen, que no usa ningún servicio. Sobre las tablas de solo inserción
  (`identity.audit_events`, `identity.consents`) `saber_app` tiene únicamente `INSERT` y
  `SELECT`.
- **Justificación**: principio IX (mínimo privilegio) y FR-035 (auditoría inmodificable desde la
  aplicación, garantizado por la base de datos y no solo por el código).
- **Alternativas**: un único usuario de aplicación (no cumple mínimo privilegio).

### R-08. Comunicación entre contextos: eventos de dominio y outbox

- **Decisión**: bus de eventos en proceso para reacciones síncronas dentro de la misma
  transacción y tabla `shared.outbox_events` (patrón outbox transaccional) para reacciones
  asíncronas. Una tarea periódica del worker reclama eventos con
  `SELECT … FOR UPDATE SKIP LOCKED`, los despacha a sus manejadores y los marca como procesados;
  los manejadores son idempotentes (clave `event_id`). Los eventos procesados se purgan a los
  7 días.
  - Precisión (2026-10-06): el bus en proceso tiene dos fases. `in_transaction` corre antes del
    `COMMIT` con la misma sesión (por ejemplo, escribir el outbox); si falla, se revierte todo.
    `after_commit` corre después del `COMMIT` para efectos fuera de la base de datos (por
    ejemplo, invalidar la caché de `auth_epoch`); sus fallos se registran y no deshacen nada. Lo
    que deba ocurrir de forma confiable va al outbox, nunca a `after_commit`.
- **Justificación**: el correo de invitación, el enlace de acceso, los avisos de supresión y la
  supresión misma deben ocurrir si y solo si la transacción que los origina se confirma.
- **Alternativas**: publicar directamente a Celery tras el commit (se pierden eventos si el
  proceso cae entre commit y publicación); LISTEN/NOTIFY (no persiste si no hay oyente).
- **ADR**: [0004-outbox-transaccional](../../docs/adr/0004-outbox-transaccional.md).

### R-09. Tareas en segundo plano y programadas

- **Decisión**: Celery (worker) y Celery Beat sobre Redis. Tareas de 001:
  `dispatch_outbox` (cada 5 s), `expire_invitations` (cada hora), `process_retention`
  (diaria, 02:00 America/Bogota: avisos a 30 días y supresiones automáticas FR-034a/b/c),
  `process_deletion_requests` (cada 15 min), `purge_expired_auth_artifacts` (diaria).
- **Justificación**: definido en el kit; las reglas de conservación de datos necesitan
  ejecución programada confiable.
- **Alternativas**: APScheduler dentro de la API (se duplica con varias réplicas); cron del
  sistema (fuera de `docker compose up`, viola el principio X).

---

## B. Autenticación institucional (Microsoft Entra ID)

### R-10. Librería OIDC

- **Decisión**: Authlib (`authlib.integrations.starlette_client`) como cliente OIDC
  confidencial con flujo *authorization code* + PKCE (S256), resuelto completamente en el
  backend. El frontend nunca ve tokens de Microsoft.
- **Justificación**: Authlib es asíncrono (usa `httpx`), se integra con Starlette/FastAPI,
  descubre la configuración por `.well-known/openid-configuration`, valida firma, `iss`, `aud`,
  `exp` y `nonce` del ID token y soporta PKCE en clientes confidenciales.
- **Alternativas**: MSAL para Python (API síncrona basada en `requests`; bloquea el bucle de
  eventos o exige hilos; aporta caché de tokens que no necesitamos porque no llamamos a APIs de
  Microsoft).
- **ADR**: [0005-autenticacion-entra-id-e-invitados](../../docs/adr/0005-autenticacion-entra-id-e-invitados.md).

### R-11. Restricción al inquilino de Unilibre (FR-002)

- **Decisión**: tres capas: (1) registro de la aplicación como *single tenant* en el Entra ID
  de Unilibre; (2) autoridad específica del inquilino
  (`https://login.microsoftonline.com/{TENANT_ID}/v2.0`), nunca `common` ni `organizations`;
  (3) validación explícita en el backend de que `tid == ENTRA_TENANT_ID` y de que `iss`
  corresponde a ese inquilino. Si falla, no se crea cuenta y se redirige a
  `/ingresar?error=tenant_not_allowed` con el mensaje de FR-002.
- **Justificación**: defensa en profundidad; un error de configuración en el registro no debe
  abrir el acceso a cualquier cuenta Microsoft.
- **Alternativas**: confiar solo en el registro *single tenant* (un único punto de falla).

### R-12. Identificador estable y datos tomados del directorio (FR-004, FR-005)

- **Decisión**: la cuenta institucional se identifica por el par (`tid`, `oid`) del ID token.
  Se solicitan solo los alcances `openid profile email`; se toman los claims `name` y `email`
  (o `preferred_username` si `email` no viene). No se llama a Microsoft Graph.
- **Justificación**: `oid` es inmutable por persona dentro del inquilino; el correo y el nombre
  pueden cambiar y se actualizan en cada ingreso (escenario 1.3). No pedir Graph cumple la
  minimización (principio V).
- **Alternativas**: `sub` (es distinto por aplicación; válido pero menos útil si TI audita por
  `oid`); correo como clave (cambia con renombres de cuenta).

### R-13. Estado OIDC y protección del flujo

- **Decisión**: `state`, `nonce` y `code_verifier` se guardan en una cookie de sesión
  temporal firmada y cifrada (`SessionMiddleware` de Starlette con `itsdangerous`), `HttpOnly`,
  `Secure`, `SameSite=Lax` (necesario para volver desde Microsoft), ruta `/api/auth/microsoft`,
  10 minutos de vida. Tras el *callback* se borra.
- **Justificación**: no requiere almacenamiento en servidor y queda ligado al navegador que
  inició el flujo.
- **Alternativas**: guardar el estado en Redis (más piezas para el mismo resultado).

---

## C. Sesión propia de la aplicación

### R-14. Tokens de sesión

- **Decisión**:
  - **Token de acceso**: JWT HS256 de 10 minutos, firmado con un secreto de 256 bits de
    variable de entorno (con `kid` para rotación). Claims: `sub` (id de usuario), `sid` (id de
    sesión), `roles`, `epoch` (época de autorización, ver R-16), `priv` (ver R-15), `iat`,
    `exp`. Se entrega en el cuerpo JSON y el frontend lo guarda **solo en memoria**.
  - **Token de renovación**: valor opaco aleatorio de 256 bits; en base de datos se guarda solo
    su hash SHA-256. Cookie `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/auth`.
    Rotación en cada uso con detección de reutilización por familia: si se presenta un token ya
    rotado, se revoca toda la familia (todas las sesiones derivadas).
  - **Duración para sesiones de aprendizaje**: 7 días de inactividad y 30 días absolutos.
- **Justificación**: definido en el kit (JWT corto + *refresh* rotativo en cookie). La
  inactividad de 7 días coincide con el plazo sin conexión de FR-038: quien pasa más de 7 días
  sin validar con el servidor ya no puede renovar y debe autenticarse de nuevo. Como el token de
  acceso viaja en la cabecera `Authorization` y la cookie solo sirve en `/api/auth/refresh` con
  `SameSite=Strict`, no hay superficie de CSRF en la API.
- **Alternativas**: sesión de servidor con cookie en todas las peticiones (exige protección CSRF
  en toda la API); token de acceso en `localStorage` (expuesto a XSS).
- **Dependencia nueva**: `PyJWT`.

### R-15. Sesiones con privilegios (ASVS 3.3.2 nivel 2)

- **Decisión**: el token de acceso solo lleva `priv=true` si el usuario tiene un rol con
  privilegios (Docente, Director de programa, Administrador) **y** su última autenticación
  real (`auth_time`) fue hace menos de 12 horas **y** su última actividad privilegiada fue hace
  menos de 30 minutos. Al crear la sesión o al reautenticarse, `last_privileged_activity_at`
  se inicializa con `auth_time`, de modo que una autenticación reciente habilita de inmediato
  las funciones privilegiadas. Los endpoints de docentes y administración exigen `priv=true`; si falta,
  responden `401` con el tipo de problema `reauthentication-required` y el frontend redirige al
  ingreso (con Microsoft suele ser transparente si su sesión sigue activa).
- **Justificación**: ASVS 4.0.3 V3.3.2 nivel 2 pide reautenticación cada 12 horas o tras
  30 minutos de inactividad. Aplicarlo a todas las sesiones contradiría FR-038 (7 días sin
  conexión) y obligaría a los invitados a pedir un enlace por correo cada 12 horas. Separar el
  nivel de la sesión según la operación cumple ambos: las funciones con datos de terceros
  quedan bajo ASVS nivel 2, y la práctica personal queda bajo la regla de la especificación.
  La desviación se registra en *Complexity Tracking* del plan.
- **Alternativas**: sesiones cortas para todos (incumple FR-038 y la experiencia móvil);
  sesiones largas para todos (incumple ASVS nivel 2 para funciones administrativas).

### R-16. Revocación inmediata (FR-010, FR-029, escenario 5.4)

- **Decisión**: cada usuario tiene una `auth_epoch` (entero) que se incrementa al desactivar la
  cuenta, revocar o vencer el acceso de invitado, revocar la autorización de datos, retirar
  roles o solicitar la supresión. El incremento revoca además todos sus tokens de renovación.
  La API compara en cada petición el `epoch` del token de acceso con el valor vigente, guardado
  en Redis (con respaldo en la base de datos si Redis no responde). Si no coincide, responde
  `401` con el tipo de problema que explica la causa.
- **Justificación**: "toda sesión abierta del invitado termina" y "pierde el acceso en su
  siguiente acción" no se cumplen esperando a que venzan 10 minutos de token.
- **Alternativas**: lista de tokens revocados (crece sin límite); consultar la base de datos en
  cada petición sin caché (carga innecesaria).

### R-17. Uso sin conexión y revalidación (FR-038, FR-039)

- **Decisión**: el frontend guarda en IndexedDB una instantánea de `/api/v1/me` y la marca
  `lastValidatedAt` (actualizada en cada renovación exitosa). Sin conexión, la app permite usar
  las funciones disponibles sin red mientras `ahora − lastValidatedAt ≤ 7 días`; después
  bloquea y pide reconectarse. Al recuperar la red, la cola de sincronización (spec 003)
  **primero** llama a `POST /api/auth/refresh` y luego a `GET /api/v1/me`; solo si ambas
  responden bien y `/me` indica acceso vigente y autorización vigente, sincroniza. Si fallan,
  muestra la causa indicada por el tipo de problema (`account-disabled`, `guest-access-expired`,
  `guest-access-revoked`, `consent-required`, `session-expired`) y conserva o descarta la cola
  según FR-039.
- **Justificación**: el servidor nunca acepta datos sin validar acceso y autorización; el
  cliente aplica el límite de 7 días sin depender de la red.
- **Alternativas**: tokens de acceso de 7 días (inaceptable para revocación con conexión).
- **Dependencia nueva**: `dexie` (frontend; se reutiliza en 003 para lecciones y respuestas).

---

## D. Invitados y enlaces de acceso

### R-18. Formato y consumo de enlaces (FR-007, FR-013)

- **Decisión**:
  - Tokens aleatorios de 256 bits; en base de datos solo su hash SHA-256; un solo uso.
  - Vigencias: enlace de invitación 7 días; enlace de ingreso 15 minutos (valores por defecto
    configurables en `identity.settings`).
  - El enlace del correo apunta al **frontend** con el token en el fragmento:
    `https://<host>/acceso#t=<token>`. La página muestra el botón "Ingresar" y solo al pulsarlo
    hace `POST /api/auth/guest/sessions`. El fragmento no viaja al servidor ni a registros del
    proxy ni en la cabecera `Referer`.
  - `POST /api/auth/guest/link-requests` responde siempre `202` con el mismo cuerpo, exista o no
    el correo (FR-013), y el trabajo real ocurre de forma asíncrona.
- **Justificación**: los filtros de seguridad de correo (por ejemplo, Safe Links) abren los
  enlaces con GET para analizarlos; si el GET consumiera el token, el invitado recibiría un
  enlace ya usado. El fragmento evita fugas del token en registros.
- **Alternativas**: consumir el token en un GET al backend (se quema con los escáneres).

### R-19. Los tokens nunca quedan guardados en claro

- **Decisión**: la API no genera el token. Al crear o reenviar una invitación, o al pedir un
  enlace, registra un evento en el outbox con el id de la invitación. El manejador del worker
  genera el token, guarda su hash y envía el correo en la misma unidad de trabajo.
- **Justificación**: el token en claro solo existe en memoria del worker y en el correo; no
  queda en el outbox, en Redis ni en registros.
- **Alternativas**: guardar el token cifrado en el payload del outbox (exige gestionar otra
  clave y purgar payloads).

### R-20. Dominios institucionales (FR-008)

- **Decisión**: variable de entorno `INSTITUTIONAL_EMAIL_DOMAINS` (lista separada por comas,
  por ejemplo `unilibre.edu.co`), que incluye subdominios. Las invitaciones a esos dominios se
  rechazan con el tipo de problema `institutional-email-not-invitable`.
- **Justificación**: el dominio es configuración de despliegue, no regla de negocio editable.

### R-21. Lotes de invitaciones (FR-009, SC-005)

- **Decisión**: carga de CSV (UTF-8, columnas `correo`, `nombre` opcional, `vence` opcional en
  formato `AAAA-MM-DD`; máximo 500 filas) o JSON equivalente. Dos pasos: `POST
  /api/v1/invitation-batches` valida y devuelve el reporte por fila con estado
  `pending_confirmation`; `POST /api/v1/invitation-batches/{id}/confirmation` crea y encola
  solo las filas válidas. Un lote sin confirmar vence a las 24 horas.
- **Justificación**: SC-005 pide 200 invitaciones con reporte en menos de 5 minutos de trabajo;
  validar 500 filas es inmediato y el envío es asíncrono.
- **Alternativas**: XLSX (se agrega en 002 para ítems; aquí basta CSV, que exporta cualquier hoja
  de cálculo).

---

## E. Autorización, datos personales y conservación

### R-22. Modelo de permisos

- **Decisión**: RBAC con permisos declarados en código (`identity/domain/permissions.py`): cada
  rol se asocia a un conjunto de permisos (`invitations:manage_own`, `invitations:manage_all`,
  `users:manage`, `groups:manage`, `groups:read_own_students`, `programs:read_aggregated`,
  `programs:manage`, `settings:manage`, `audit:read`, `policy:publish`, `deletions:read`; la
  lista completa es el enum `Permission` del contrato). Los permisos de un usuario son la unión de
  sus roles (FR-023). Las reglas de alcance (invitaciones propias, grupos propios, programas
  asignados) se verifican en la capa de aplicación. Un recurso fuera del alcance responde `404`
  (no revela que existe); una función no permitida responde `403`.
- **Justificación**: cinco roles fijos definidos por la especificación; una tabla de permisos
  editable sería complejidad sin requisito (YAGNI).
- **Alternativas**: permisos en base de datos editables por el administrador (no lo pide la spec).

### R-23. Registros sin datos personales (principio V, FR-036)

- **Decisión**: logs JSON con `structlog`. Un procesador final elimina o enmascara claves
  sensibles (`email`, `name`, `correo`, `nombre`, `token`, `authorization`, `cookie`, `code`) y
  valores con forma de correo electrónico. Los eventos de negocio se registran con el id
  (UUID v7) del usuario, nunca con su nombre o correo. Los rechazos de ingreso se registran con
  la causa (`tenant_not_allowed`, `invalid_state`, `link_used`, …) sin correo ni token. Una
  prueba unitaria verifica el procesador y una prueba de integración revisa los logs de los
  flujos de ingreso.
- **Justificación**: "cero datos personales en logs" debe ser verificable.

### R-24. Auditoría (FR-035, SC-004)

- **Decisión**: tabla `identity.audit_events` de solo inserción (garantizado por permisos de
  base de datos, R-07). Cada evento guarda actor (id), acción, tipo e id del objeto, id del
  usuario afectado, fecha y hora, y un detalle JSON **sin datos personales** (por ejemplo, los
  roles antes y después, nunca el correo invitado). La escritura de auditoría ocurre en la misma
  transacción que la acción. Consulta solo para Administrador.
- **Justificación**: al suprimir a una persona, la auditoría no necesita modificarse porque solo
  contiene identificadores que dejan de resolverse a una persona (FR-033).

### R-25. Supresión de datos (FR-032, FR-033, FR-034a/b/c)

- **Decisión**:
  - Solicitud voluntaria: el usuario pasa a `deletion_pending`, se incrementa su `auth_epoch` y
    se revocan sus sesiones de inmediato. Se crea la solicitud con fecha límite = 15 días
    hábiles en Colombia. El worker la procesa (objetivo: menos de 24 horas).
  - Procesamiento: se borran perfil, asignaciones de rol, membresías, tokens y autorizaciones
    vinculadas a datos de contacto; la fila del usuario queda como **lápida** con su UUID,
    `status = deleted` y sin nombre, correo ni `oid`. Se publica el evento `UserErased` para que
    los demás contextos (002 en adelante) anonimicen lo suyo. Las estadísticas y la auditoría
    conservan solo el UUID, que ya no identifica a nadie.
  - Como el `oid` se borra, si la persona vuelve a ingresar se crea una cuenta nueva sin
    historial (escenario 7.3).
  - Conservación automática: se calcula a partir de fechas, sin estados intermedios. Invitados:
    `fin_de_acceso = mínimo(revocado_en, vence_en)`; aviso en `fin + 60 días`, supresión en
    `fin + 90 días`. Institucionales: aviso en `último_ingreso + 335 días`, supresión en
    `último_ingreso + 365 días`. Ingresar o renovar el acceso mueve las fechas y cancela el
    proceso de forma natural (FR-034c). `retention_notice_sent_at` evita avisos duplicados y se
    limpia al ingresar o renovar.
- **Justificación**: cumple la Ley 1581 sin depender de procesos manuales.
- **Dependencia nueva**: `holidays` (cálculo de días hábiles con festivos de Colombia, que
  cambian cada año por la Ley Emiliani).
- **Alternativas**: borrar la fila del usuario (rompe la integridad referencial de las
  estadísticas futuras); tabla de festivos mantenida a mano (propensa a errores).

### R-26. Exportación de "Mis datos" (FR-031)

- **Decisión**: `GET /api/v1/me/data-export` devuelve un JSON legible
  (`Content-Disposition: attachment`) con identidad, perfil, roles, grupos, historial de
  autorizaciones e invitación de origen. Las especificaciones futuras agregan sus secciones
  mediante una interfaz de "proveedores de exportación" por contexto.
- **Justificación**: un formato legible y estructurado cumple el derecho de consulta.

### R-27. Política de tratamiento de datos

- **Decisión**: versiones guardadas en `identity.policy_versions` (texto Markdown, número de
  versión, fecha de vigencia). La migración inicial carga la versión 1 desde
  `backend/seeds/politica_tratamiento_datos_v1.md`. Publicar una nueva versión (Administrador)
  hace que todos deban aceptarla (FR-017).
- **Dependencia externa**: el texto definitivo debe redactarlo o aprobarlo la oficina jurídica
  de Unilibre; el borrador de la semilla se marca como tal.

### R-28. Primer administrador

- **Decisión**: comando CLI `saber-uli identity grant-admin --email <correo>` ejecutado con
  `docker compose run --rm api …`, sobre un usuario institucional que ya ingresó una vez. Queda
  auditado con actor `system`.
- **Justificación**: no hay forma segura de asignar el primer administrador desde la interfaz.
- **Alternativas**: variable de entorno con correos administradores (otorga privilegios por
  configuración, difícil de auditar).

### R-29. Parámetros configurables

- **Decisión**: tabla `identity.settings` (clave/valor tipado) editable por el Administrador:
  plazo máximo de acceso para invitaciones de docentes (180 días), vencimiento por defecto del
  acceso de invitado (90 días), vigencia del enlace de invitación (7 días) y del enlace de
  ingreso (15 minutos).
- **Justificación**: FR-006a pide un plazo configurable por un administrador; los demás valores
  son supuestos de la especificación que conviene poder ajustar sin desplegar código.

---

## F. Correo, límites y operación

### R-30. Envío de correo

- **Decisión**: contexto `notifications` con el puerto `EmailSender` y un adaptador SMTP con
  `smtplib` de la biblioteca estándar (el worker de Celery es síncrono). Plantillas HTML y de
  texto en español con Jinja2 (autoescape activo). En desarrollo, Mailpit.
- **Dependencia nueva**: `jinja2`.
- **Dependencia externa**: servidor SMTP de producción (oficina de TI o proveedor).
- **Alternativas**: `aiosmtplib` (innecesario fuera del bucle asíncrono de la API).

### R-31. Limitación de peticiones (principio IX)

- **Decisión**: librería `limits` con almacenamiento en Redis, aplicada como dependencia de
  FastAPI:
  - `POST /api/auth/guest/link-requests`: 5 por hora por hash de correo y 20 por hora por IP.
  - `POST /api/auth/guest/sessions`: 10 por minuto por IP.
  - `GET /api/auth/microsoft/*` y `POST /api/auth/refresh`: 30 por minuto por IP.
  - Resto de la API: 300 por minuto por usuario.
  Se responde `429` con `Retry-After`.
- **Dependencia nueva**: `limits`.
- **Alternativas**: `slowapi` (envoltorio de `limits` con mantenimiento irregular); límites solo
  en Nginx (no conoce usuarios ni correos).

### R-32. Observabilidad

- **Nota sobre imágenes sin root (principio X)**: la regla se verifica sobre el proceso
  principal de cada servicio. Las imágenes propias (`api`, `worker`, `beat`, `migrate`,
  `proxy`) arrancan sin root. `postgres:18` y `redis:8-alpine` inician su entrypoint como root
  solo para preparar el volumen y luego ejecutan el servidor con un usuario sin privilegios
  (`gosu`/`su-exec`); `mailpit` y `oidc` se fijan con `user:` explícito en Compose. Una prueba
  de infraestructura comprueba con `docker compose top` que ningún proceso principal corre con
  UID 0.
- **Decisión**: `structlog` (JSON), `GET /api/health` (proceso vivo) y `GET /api/ready` (base de
  datos y Redis disponibles) en la API; *health checks* de Docker para todos los servicios; trazas
  OpenTelemetry desactivadas por defecto (`OTEL_ENABLED=false`).
- **Justificación**: principio X.

### R-33. Proxy y HTTPS

- **Decisión**: Nginx sirve el frontend compilado y redirige `/api/` a la API. Cabeceras:
  `Service-Worker-Allowed: /` y `Cache-Control: no-cache` para `sw.js` y `manifest.webmanifest`;
  `Content-Security-Policy` estricta (sin `unsafe-inline` en scripts), `Strict-Transport-Security`
  en producción, `X-Content-Type-Options`, `Referrer-Policy: no-referrer` y `Permissions-Policy`.
  En producción, `compose.prod.yaml` termina TLS en Nginx con certificados montados.
- **Justificación**: la PWA y las cookies `Secure` requieren HTTPS fuera de `localhost`.

---

## G. Frontend

### R-34. Pila del frontend

- **Decisión** (del kit): React + TypeScript + Vite; `vite-plugin-pwa` (Workbox); TanStack
  Router y TanStack Query; Zustand para estado de interfaz (incluido el token de acceso en
  memoria); Tailwind CSS + shadcn/ui; Motion; react-hook-form + zod; cliente generado con
  `orval` desde `contracts/openapi.yaml`; Dexie (R-17).
- **Agregado**: `i18next` + `react-i18next` para tener i18n preparado con es-CO por defecto
  (principio VIII).
- **Alternativas para i18n**: FormatJS/react-intl (más pesado para un solo idioma inicial).

### R-35. Rutas de la interfaz en 001

- **Decisión**: `/ingresar`, `/acceso` (consumo del enlace de invitado), `/bienvenida/datos`
  (autorización), `/bienvenida/perfil`, `/inicio` (marcador hasta la spec 003), `/mi-cuenta`,
  `/mi-cuenta/datos` (consulta, descarga y supresión), `/mi-cuenta/autorizacion`,
  `/invitaciones` (Docente y Administrador), `/admin/usuarios`, `/admin/grupos`,
  `/admin/programas`, `/admin/supresiones`, `/admin/politica`, `/admin/parametros`,
  `/admin/auditoria`, `/grupos` (Docente).
- **Justificación**: cubre las 8 historias de usuario; las rutas usan español porque son texto
  visible para el usuario.

---

## H. Pruebas

### R-36. Estrategia de pruebas

- **Decisión**:
  - **Unitarias de dominio** (pytest): reglas de invitación, vencimientos, conservación, días
    hábiles, permisos y alcance, máquina de estados, rotación de tokens.
  - **Integración** (pytest-asyncio + Testcontainers `postgres:18` y `redis:8`): repositorios,
    migraciones, permisos de base de datos (que `UPDATE` y `DELETE` sobre auditoría fallen),
    outbox, tareas programadas; el proveedor OIDC se simula con `respx` y claves JWK generadas
    en la prueba.
  - **Contrato**: Schemathesis contra `contracts/openapi.yaml`.
  - **Frontend**: Vitest + Testing Library + MSW.
  - **Extremo a extremo** (Playwright, viewport móvil): se levanta el stack con el perfil `e2e`
    de Compose, que añade `mock-oauth2-server` (proveedor OIDC de prueba configurable con
    `tid` válido e inválido) y Mailpit (los enlaces de invitado se leen de su API). Incluye
    accesibilidad con `@axe-core/playwright` y el escenario sin conexión de FR-038.
  - **Lighthouse CI** sobre el shell de la PWA.
- **Justificación**: principio IV; ninguna prueba depende del Entra ID real.
- **Dependencias nuevas (desarrollo)**: `respx`, `testcontainers`, `schemathesis`,
  `import-linter`, `mock-oauth2-server` (imagen solo para pruebas).

### R-37. Integración continua

- **Decisión**: GitHub Actions con trabajos: `backend-quality` (ruff, mypy estricto,
  import-linter), `backend-tests` (unitarias + integración, cobertura ≥ 80 % en `domain` y
  `application`), `contract` (Schemathesis), `frontend-quality` (eslint, tsc, Vitest),
  `e2e` (Playwright + axe), `lighthouse`, `build` (imágenes) y `security` (Trivy sobre
  imágenes y sistema de archivos; Dependabot para actualizaciones).

### R-39. Herramientas de soporte

- **Decisión**: se adoptan estas dependencias auxiliares, todas de uso acotado:

  | Dependencia | Uso | Justificación | Alternativa descartada |
  |-------------|-----|---------------|------------------------|
  | `pydantic-settings` | backend | Configuración por entorno tipada y validada al arrancar (principio X) | Leer `os.environ` a mano (sin validación ni tipos) |
  | `pytest-cov` | backend, desarrollo | Medir y exigir la cobertura del 80 % en CI (principio IV) | `coverage` directo (mismo motor, peor integración con pytest) |
  | `detect-secrets` | pre-commit | Bloquear secretos antes del commit (principio IX) | Solo Trivy en CI (detecta tarde, cuando el secreto ya está en el historial) |
  | `@hookform/resolvers` | frontend | Conecta los esquemas zod con react-hook-form | Validación duplicada a mano |
  | `@testing-library/user-event` | frontend, desarrollo | Simula interacción real de teclado y puntero, necesaria para probar accesibilidad | `fireEvent` (no reproduce la secuencia real de eventos) |
  | `typescript-eslint`, `eslint-plugin-jsx-a11y` | frontend, desarrollo | Reglas de tipos y de accesibilidad estática (principio VIII) | Solo axe en e2e (detecta tarde) |
  | `actionlint` | CI | Valida la sintaxis y expresiones del flujo de GitHub Actions | Descubrir errores al ejecutar el flujo |
  | `nginxinc/nginx-unprivileged` (imagen) | proxy | Nginx que corre sin root (principio X) | `nginx` oficial (arranca como root) |
- **Justificación**: cada una evita trabajo manual propenso a errores o hace verificable un
  principio de la constitución; ninguna agrega comportamiento en tiempo de ejecución salvo
  `pydantic-settings` y la imagen de Nginx.

---

## I. Decisiones del proyecto para especificaciones futuras

El kit pide decidir aquí la estrategia del motor adaptativo. Se registra como **propuesta** y se
confirma al planear la spec 005.

### R-38. Motor adaptativo y repaso espaciado (spec 005)

- **Decisión propuesta**: calificación tipo Elo por estudiante–afirmación (y por parte en Inglés)
  y por ítem para el MVP, detrás de un puerto `ProficiencyEstimator` que permita cambiar a TRI
  (modelo de Rasch o 2PL) cuando cada ítem tenga suficientes respuestas. Repaso espaciado con
  **FSRS** (librería `fsrs`, licencia MIT).
- **Justificación**: Elo se actualiza en línea con una sola respuesta y funciona con un banco
  pequeño. FSRS modela la memoria con más precisión que SM-2 (menos repasos para la misma
  retención) y su implementación de referencia está mantenida.
- **Alternativas**: SM-2 (más simple, pero con intervalos fijos poco precisos); TRI desde el
  inicio (requiere calibración previa con cientos de respuestas por ítem).
- **ADR**: [0007-motor-adaptativo](../../docs/adr/0007-motor-adaptativo.md) (estado: Propuesto).

---

## J. Supuestos de capacidad

- **Usuarios registrados**: hasta 40 000 (comunidad de todas las seccionales). **Concurrencia
  pico**: 2 000 usuarios activos. **Invitados**: menos de 2 000 activos.
- **Objetivos**: p95 < 300 ms en los endpoints propios (sin contar el tiempo de Microsoft);
  lote de 500 invitaciones validado en < 2 s; correos de invitación encolados enviados en
  < 1 minuto (apoya SC-007).
- Un servidor con 4 vCPU y 8 GB de RAM sostiene esta carga con una réplica de API (4 procesos
  Uvicorn) y un worker; el escalado horizontal de la API está habilitado porque la sesión no
  depende del proceso.
