# Verificación OWASP ASVS 4.0.3 nivel 2: 001 Identidad, acceso institucional e invitados

**Tarea**: T178 | **Fecha**: 2026-10-08 | **Revisó**: Opus | **Base**: revisión de seguridad
de la fase 2 (T070) y pruebas automáticas de las fases 3 a 11.

Alcance: la API (`backend/src/saber_uli`), la PWA (`frontend/src`), el proxy Nginx
(`infra/nginx`) y la configuración de Compose. Capítulos pedidos por la tarea: V2, V3, V4, V5,
V7, V8 y V13. Se listan los requisitos de nivel 1 y 2 de cada sección; las secciones que no
aplican se justifican una vez.

Estados:

- **Cumple**: con la evidencia indicada (archivo o prueba automática).
- **Desviación**: no cumple al pie de la letra por una decisión de la especificación, con
  mitigación y justificación registradas.
- **Hallazgo**: no cumple; queda una tarea abierta (sección final).
- **N/A**: no aplica a esta funcionalidad, con el motivo.

Las rutas de pruebas son relativas a `backend/tests/` salvo que empiecen por `frontend/`.

---

## V2. Autenticación

Modelo: la comunidad Unilibre se autentica en Microsoft Entra ID (OIDC, código de autorización
con PKCE, inquilino único; R-10 a R-13) y la app nunca ve contraseñas. Las personas invitadas
entran con enlaces de un solo uso enviados a su correo (R-18). No hay contraseñas propias.

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 2.1.x Seguridad de contraseñas | N/A | La app no tiene contraseñas. Las de la comunidad las gestiona Entra ID con las políticas de TI. |
| 2.2.1 Controles contra automatización | Cumple | Límites de R-31 en Redis: ingreso con Microsoft 120/min por IP, sesión de invitado 60/min por IP, pedido de enlace 20/h por IP y 5/h por correo (clave HMAC, nunca el correo), renovación 600/min por IP y 30/min por sesión; 429 con `Retry-After`. `shared/infrastructure/rate_limit.py`; `integration/shared/test_rate_limit.py`, `integration/identity/test_sign_in_link_request.py`. |
| 2.2.2 Autenticadores débiles (correo) solo como factor secundario | Desviación | Los invitados entran solo con un enlace por correo: es el modelo de FR-007 (personas externas sin cuenta Unilibre). Mitigación: el rol Invitado no tiene funciones privilegiadas ni acceso a datos de terceros; el acceso vence (90 días por defecto) y se puede revocar con efecto inmediato (R-16); cada enlace es de un solo uso. |
| 2.2.3 Aviso tras cambiar datos de autenticación | N/A | No hay datos de autenticación que cambiar en la app. |
| 2.3.1 Códigos de activación aleatorios y de vida corta | Cumple (con justificación) | El enlace de invitación es la activación: 256 bits de `secrets`, solo su SHA-256 en la base, un solo uso, 7 días (configurable de 1 a 30) para dar tiempo a leer el correo; revocable por quien invitó. `identity/infrastructure/link_tokens.py`; `integration/identity/test_guest_session_api.py`. |
| 2.3.2, 2.3.3 Registro y renovación de autenticadores del usuario | N/A | No hay autenticadores propios que registrar o renovar. |
| 2.4.x Almacenamiento de credenciales | N/A | Sin contraseñas. Los secretos de alta entropía (renovación, enlaces) se guardan solo como SHA-256, que basta para valores aleatorios de 256 bits. |
| 2.5.x Recuperación de credenciales | N/A | No hay credencial que recuperar: Microsoft gestiona las cuentas institucionales, y un invitado pide un enlace de ingreso nuevo (V2.7). La respuesta es siempre 202 con el mismo cuerpo, exista o no el correo (FR-013). |
| 2.6.x Secretos de consulta | N/A | No se usan. |
| 2.7.1 Sin OOB en claro por SMS o teléfono | Cumple | No hay SMS ni llamadas; el canal es el correo (ver 2.2.2). |
| 2.7.2 El código OOB vence a los 10 minutos | Cumple | El enlace de ingreso vence a los 10 minutos por defecto y un administrador puede ponerlo entre 5 y 10 (T178a: antes 15, de 5 a 60; la migración 0007 recorta valores guardados mayores). `identity/domain/settings.py`; `unit/identity/test_settings.py`, `integration/identity/test_settings_repository.py`. |
| 2.7.3 Un solo uso y solo para la solicitud original | Cumple | El enlace se consume con bloqueo de fila y se marca usado en la misma transacción que abre la sesión; al emitir un enlace nuevo, los anteriores sin usar del mismo propósito quedan invalidados (`identity/domain/access_link.py`). `unit/identity/test_access_links.py`, `integration/identity/test_guest_session_api.py`, `test_sign_in_link_handler.py`. |
| 2.7.4 Canal independiente y seguro | Cumple | El correo es un canal distinto del navegador. El token va en el fragmento (`/acceso#t=…`): no llega al servidor, a los registros ni a `Referer`, y no se consume con un GET (los escáneres de correo no lo queman). |
| 2.7.5 El verificador guarda solo un hash | Cumple | `identity.access_links.token_hash` (SHA-256, único); el token en claro solo existe en el correo. |
| 2.7.6 Código generado con CSPRNG (≥ 20 bits) | Cumple | 256 bits de `secrets.token_urlsafe`. |
| 2.8.x, 2.9.x OTP y criptografía | N/A | No se usan. |
| 2.10.1 Secretos entre servicios no estáticos | Desviación | PostgreSQL y Redis usan contraseñas por rol, desde variables de entorno, en la red interna de Compose (riesgo aceptado: no hay gestor de identidades de servicio). Cada servicio recibe solo su URL; `saber_bi` sin acceso a `identity` (T029). |
| 2.10.2 Sin credenciales por defecto | Cumple | Las claves de firma y cookies exigen ≥ 256 bits, y con `PUBLIC_BASE_URL` https la API y el worker no arrancan si la contraseña de PostgreSQL o Redis es la de `.env.example` (T178c). `config.py`; `unit/shared/test_config.py::test_produccion_rechaza_la_contrasena_de_ejemplo`. |
| 2.10.3, 2.10.4 Secretos fuera del código | Cumple | `${VAR:?}` en Compose, `.env` ignorado por Git, detect-secrets en pre-commit, Trivy en CI; `ConfigError` sin valores. `infra/test_containers.py::test_las_variables_de_la_prueba_cubren_env_example`. |

Cuentas institucionales: `tid` y `iss` validados contra el inquilino de Unilibre (además del
registro de inquilino único), `aud`, `nonce`, `exp` e `iat` obligatorios
(`identity/infrastructure/entra_id.py`; `integration/identity/test_entra_adapter.py`,
`test_microsoft_login_flow.py`). El MFA de esas cuentas depende de las políticas de acceso
condicional de TI (ver V4.3.1).

## V3. Gestión de sesiones

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 3.1.1 Sin tokens de sesión en la URL | Cumple | Acceso en `Authorization: Bearer`, renovación en cookie, enlaces de invitado en el fragmento. |
| 3.2.1 Token nuevo al autenticarse | Cumple | Cada ingreso crea sesión, familia de renovación y token de acceso nuevos (`SessionService.open_session`). |
| 3.2.2 Al menos 64 bits de entropía | Cumple | Renovación de 256 bits; JWT firmado con claves de ≥ 256 bits. |
| 3.2.3 Almacenamiento seguro en el navegador | Cumple | Token de acceso solo en memoria (`frontend/src/features/auth/session-store.ts`); renovación en cookie `HttpOnly`. |
| 3.2.4 Algoritmos criptográficos aprobados | Cumple | `secrets` (CSPRNG), HS256, SHA-256, HMAC para las claves de Redis. |
| 3.3.1 Cerrar sesión y vencer invalida el token | Cumple | Logout revoca la familia de renovación y pone el `sid` en la lista de sesiones revocadas de Redis, que `AccessGuard` consulta en cada petición (corregido en T070). `integration/identity/test_refresh_logout.py`, `test_auth_dependency.py`. |
| 3.3.2 Reautenticación cada 12 h o tras 30 min de inactividad | Desviación (registrada en plan.md) | Las funciones privilegiadas (docentes, directores y administradores) exigen `priv`: autenticación de hace menos de 12 h y actividad privilegiada en los últimos 30 min (R-15, ADR 0005). La práctica personal usa sesiones de aprendizaje de 7 días de inactividad y 30 absolutos por FR-038 (uso sin conexión); no dan acceso a datos de terceros. `unit/identity/test_session_policy.py`, `integration/identity/test_auth_dependency.py`. |
| 3.3.3 Cerrar las demás sesiones al cambiar un factor | N/A | No hay factores que cambiar en la app. |
| 3.3.4 Ver y cerrar las sesiones activas | Cumple | Mi cuenta lista las sesiones activas (forma de ingreso, inicio y última actividad, sin IP ni dispositivo) y permite cerrar una o todas las demás; la sesión cerrada entra en la lista de revocadas y deja de servir en su siguiente petición (FR-037a, T178b). No se pide reingresar antes de cerrar: es una acción de protección y la sesión actual ya es válida. `identity/application/my_sessions.py`; `integration/identity/test_my_sessions_api.py`, `frontend/tests/e2e/us1-sessions.spec.ts`. |
| 3.4.1 Cookie `Secure` | Cumple | Siempre que `PUBLIC_BASE_URL` es https (producción); en http solo se admite localhost (R-14, precisión de T120). |
| 3.4.2 Cookie `HttpOnly` | Cumple | Renovación y estado OIDC. |
| 3.4.3 Cookie `SameSite` | Cumple | Renovación `Strict`; estado OIDC `Lax` (necesario para volver de Microsoft), 10 min, borrado tras el callback. |
| 3.4.4 Prefijo `__Host-` | Desviación | `__Host-` exige `Path=/`; la cookie de renovación va con `Path=/api/auth` para que solo viaje a renovar y cerrar sesión. Es *host-only* (sin `Domain`), lo que da el mismo aislamiento de dominio que el prefijo. |
| 3.4.5 Atributo `Path` preciso | Cumple | `/api/auth` (renovación) y `/api/auth/microsoft` (estado OIDC). |
| 3.5.1 Revocar autorizaciones OAuth a apps vinculadas | N/A | No hay apps de terceros vinculadas. |
| 3.5.2 Tokens de sesión, no secretos estáticos | Cumple | JWT de 10 min y renovación rotativa. |
| 3.5.3 Tokens sin estado firmados y protegidos | Cumple | Algoritmo fijo (`algorithms=["HS256"]`, nunca `none`), clave buscada por `kid` en un mapa cerrado, `exp` verificado con el reloj inyectado, claims obligatorios; la época de autorización (R-16) y la lista de revocadas cubren la revocación. `identity/infrastructure/tokens.py`; `integration/identity/test_auth_dependency.py::test_token_invalido`. |
| 3.7.1 Sesión completa o reautenticación antes de operaciones sensibles | Cumple | Las operaciones privilegiadas exigen `priv` (401 `reauthentication-required`); la supresión de la cuenta exige una sesión válida y la confirmación escrita `ELIMINAR`. |

Además: la renovación rota en cada uso y, si se presenta un token ya rotado pasados 30 s,
revoca la familia y lo audita (`session.reuse_detected`, R-14).

## V4. Control de acceso

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 4.1.1 Control en el servidor | Cumple | `AccessGuard` y `require_permission(...)` en cada ruta; las guardias del frontend solo orientan la navegación. |
| 4.1.2 Atributos no manipulables por el usuario | Cumple | Roles y `priv` van en el JWT firmado y se contrastan con `auth_epoch`, que sube al cambiar roles o estado (R-16). |
| 4.1.3 Mínimo privilegio | Cumple | Matriz de permisos del contrato; docentes solo con sus invitaciones y grupos; permisos de base de datos por rol (auditoría y consentimientos de solo inserción, sin `DELETE` de usuarios). `integration/identity/test_db_grants.py`. |
| 4.1.5 Falla segura | Cumple | Niega por defecto: sin token 401, sin autorización de datos 403 `consent-required`, sin `priv` 401, sin permiso 403. |
| 4.2.1 Referencias directas inseguras (IDOR) | Cumple | `/me/*` usa solo el `sub` del token; un docente que pide la invitación o el grupo de otro recibe 404. `integration/identity/test_invitations_api.py`, `test_teacher_groups_api.py`, `test_groups_api.py`. |
| 4.2.2 CSRF | Cumple | La API se autoriza por cabecera `Authorization`; la cookie solo sirve en `/api/auth/refresh` y `/logout`, con `SameSite=Strict` y `X-Requested-With` obligatorio. |
| 4.3.1 MFA en interfaces de administración | Depende de TI | Los administradores son cuentas institucionales autenticadas por Entra ID: el MFA lo impone el acceso condicional del inquilino. Queda pedido a TI en quickstart.md (sección 2). |
| 4.3.2 Sin listado de directorios ni metadatos expuestos | Cumple | Nginx sirve solo `dist/` (sin `autoindex`) y `/api`; `.git` y fuentes no están en la imagen (`.dockerignore`). |
| 4.3.3 Autorización adicional para funciones de menor confianza | Cumple | Sesión privilegiada (R-15) y protección del último administrador. `integration/identity/test_last_admin_concurrency.py`. |

## V5. Validación, saneamiento y codificación

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 5.1.1 Contaminación de parámetros HTTP | Cumple | FastAPI tipa cada parámetro de consulta con un único valor. |
| 5.1.2 Asignación masiva | Cumple | Modelos Pydantic de entrada con `extra="forbid"` (contrato con `additionalProperties: false`). |
| 5.1.3 Validación positiva de entradas | Cumple | Esquemas Pydantic alineados con el contrato; Schemathesis prueba las 52 operaciones con datos generados. `contract/test_openapi_contract.py`. |
| 5.1.4 Datos estructurados con tipos fuertes | Cumple | Correos con patrón y máximo de 254 caracteres, códigos y versiones con patrón, fechas con zona, UUID, enumeraciones cerradas; lote CSV con encabezado y columnas fijas. |
| 5.1.5 Redirecciones solo a destinos permitidos | Cumple | `return_to` solo admite rutas internas (empieza por `/`, no por `//` ni `/\`). `identity/api/microsoft_router.py::_safe_return_to`; `integration/identity/test_microsoft_login_flow.py`. |
| 5.2.1 HTML de editores saneado | Cumple | La política se escribe en Markdown y se muestra con `react-markdown` con `skipHtml`, sin `rehype-raw` (`frontend/src/shared/ui/PolicyMarkdown.tsx`). |
| 5.2.2 Datos no estructurados saneados | Cumple | Nombres y textos libres con longitud máxima; se muestran siempre escapados (5.3.1) y nunca se interpretan. |
| 5.2.3 Entradas hacia el correo | Cumple | El destinatario es solo el correo validado; los nombres van en el cuerpo, que Jinja2 escapa (`autoescape=True`, `StrictUndefined`). `notifications/infrastructure/templates.py`. |
| 5.2.4, 5.2.5 `eval` e inyección de plantillas | Cumple | No hay `eval`; las plantillas son archivos fijos y los datos del usuario entran como variables. |
| 5.2.6 SSRF | Cumple | Solo hay llamadas salientes a la autoridad configurada de Entra ID y al SMTP; ninguna URL viene del usuario. |
| 5.2.7, 5.2.8 SVG y lenguajes de plantillas del usuario | N/A | No se suben SVG ni plantillas. |
| 5.3.1, 5.3.3 Codificación de salida y XSS | Cumple | React escapa por defecto; no hay `dangerouslySetInnerHTML`; CSP con `script-src 'self'`, sin scripts en línea. `infra/nginx/security-headers.conf`; `infra/test_containers.py::test_cabeceras_de_seguridad_del_proxy`. |
| 5.3.2 Unicode | Cumple | UTF-8 de punta a punta; el CSV acepta BOM. |
| 5.3.4 SQL parametrizado | Cumple | SQLAlchemy con parámetros enlazados; las búsquedas `LIKE` escapan comodines (`contains_pattern`). |
| 5.3.6 Inyección JSON | Cumple | Solo `JSON.parse` y serialización de Pydantic. |
| 5.3.7 a 5.3.10 LDAP, comandos del SO, inclusión de archivos, XPath | N/A | No se usan; la CLI recibe rutas de archivo solo del operador. |
| 5.4.x Memoria | N/A | Python y TypeScript con memoria administrada. |
| 5.5.1 a 5.5.4 Deserialización | Cumple | Solo JSON (API, outbox y Celery con serializador JSON); no hay XML ni `pickle`. |

Exportaciones: los datos personales se exportan en JSON (US8), no en CSV, así que no aplica la
inyección de fórmulas.

## V7. Registro y manejo de errores

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 7.1.1 Sin credenciales ni tokens en registros | Cumple | Limpieza final de claves y valores sensibles en el registro JSON; el log por petición no guarda consulta ni IP. `test_no_pii_in_logs.py` (T175) recorre US1 a US8 con API y worker; `unit/shared/test_logging.py`. |
| 7.1.2 Sin otros datos sensibles | Cumple | Igual que 7.1.1; auditoría y outbox rechazan datos personales; `last_error` guarda solo la clase. **Corregido en esta revisión**: Nginx usaba el formato `main` (IP y consulta completa, donde `?q=` puede llevar un correo) y su registro de errores copiaba la petición. Ahora usa el formato `saber` (sin IP y con la ruta sin consulta) y `error_log … crit`. `infra/nginx/logging.conf`; `infra/test_containers.py::test_el_proxy_no_registra_consultas_ni_ip`. |
| 7.1.3 Eventos de seguridad registrados | Cumple | Log JSON: `auth.login_succeeded` y `auth.login_rejected` (ver 7.2.1). Auditoría en base de datos: `session.reuse_detected`, cambios de rol y estado, invitaciones, consentimientos, supresión y publicación de la política. Las respuestas 401 y 403 quedan en el log por petición con su estado. |
| 7.1.4 Información suficiente para investigar | Cumple | JSON con `timestamp`, `event`, nivel, ruta y estado; la auditoría guarda actor, sujeto, acción y fecha. |
| 7.2.1 Decisiones de autenticación registradas | Cumple | `auth.login_succeeded` y `auth.login_rejected` con `provider` (`entra_id` o `guest_link`) y causa, sin tokens ni correo (`identity/api/microsoft_router.py`, `guest_router.py`). **Corregido en esta revisión**: el ingreso de invitados no dejaba estos eventos. `integration/identity/test_guest_session_api.py::test_el_ingreso_del_invitado_queda_registrado_sin_datos_personales`. |
| 7.2.2 Decisiones de acceso fallidas registradas | Cumple | Estado 401/403 en el log por petición y tipo de problema en la respuesta. |
| 7.3.1 Codificación contra inyección en registros | Cumple | Registros en JSON (API, worker y Nginx con `escape=json`). |
| 7.3.3 Protección de los registros | Cumple | Auditoría de solo inserción para `saber_app`; los registros de contenedor quedan en el host. |
| 7.3.4 Fuente de tiempo | Cumple | Marcas en UTC con zona; el host sincroniza por NTP (requisito de producción). |
| 7.4.1 Mensaje genérico de error | Cumple | Problem Details sin valores recibidos; los 500 responden "Error interno" sin traza; `instance` sin consulta. `unit/shared/test_problems.py`. |
| 7.4.2, 7.4.3 Manejo de excepciones y último recurso | Cumple | Manejadores para errores de dominio, `ProblemException`, validación y cualquier excepción. |

Las alertas sobre eventos operativos (`rate_limit_unavailable`, `readiness_check_failed` y
otros) están en quickstart.md (T070b).

## V8. Protección de datos

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 8.1.1 Sin caché de datos sensibles en intermediarios | Cumple | `Cache-Control: no-store` en `/api` (Nginx) y en las respuestas con tokens o datos personales. `infra/nginx/locations.conf`. |
| 8.1.2 Copias temporales en el servidor | Cumple | La exportación se genera en la petición y no se guarda en disco ni en caché. |
| 8.1.3 Mínimos parámetros sensibles | Cumple | Minimización (principio V): solo `oid`, `tid`, nombre y correo de Entra ID; sin Microsoft Graph. |
| 8.1.4 Detección de volúmenes anormales | Cumple | Límites de R-31 con 429 y alerta `rate_limit_unavailable` si Redis falla. |
| 8.2.1 Cabeceras contra caché en el navegador | Cumple | Igual que 8.1.1. El service worker nunca guarda `/api` ni lo usa como respaldo de navegación (`frontend/vite.config.ts`). |
| 8.2.2 Sin datos sensibles en el almacenamiento del navegador | Desviación (FR-038) | Para el uso sin conexión, IndexedDB guarda la instantánea de `/api/v1/me` (nombre, correo, roles y estado de acceso); nunca tokens. Es lo mínimo para que la app funcione 7 días sin red. |
| 8.2.3 Se borra al terminar la sesión | Cumple | `clearOfflineSnapshot()` al cerrar sesión, al revocar la autorización, al pedir la supresión y ante cualquier respuesta que termine la sesión. `frontend/tests/e2e/offline-access.spec.ts` (T172). |
| 8.3.1 Datos sensibles en el cuerpo o las cabeceras, no en la URL | Cumple (con nota) | Tokens y datos van en el cuerpo o las cabeceras. Las búsquedas de los listados de gestión llevan el texto en `?q=` (contrato); por eso ni la API ni Nginx registran la consulta (V7.1.2). |
| 8.3.2 El usuario puede exportar y borrar sus datos | Cumple | Exportación JSON (US8, FR-031) y supresión (US7, FR-032). |
| 8.3.3 Información clara y consentimiento | Cumple | Política versionada y autorización explícita antes de usar la app (US2); revocable. |
| 8.3.4 Datos sensibles identificados | Cumple | Clasificación en data-model.md y catálogo de la exportación. |
| 8.3.5 Acceso a datos sensibles auditado | Cumple (con alcance) | Se auditan los cambios y la exportación propia. Las consultas de los listados de gestión no se auditan: la Ley 1581 no lo exige y están limitadas por rol y sesión privilegiada. |
| 8.3.6 Borrado de datos sensibles en memoria | N/A | No es controlable en Python ni en el navegador; los datos no se retienen más allá de la petición. |
| 8.3.7 Cifrado de datos que lo requieran | N/A | Ningún dato de 001 exige cifrado en reposo; los secretos de alta entropía se guardan solo como hash. TLS en tránsito (V9). |
| 8.3.8 Retención y purga | Cumple | Supresión en máximo 15 días hábiles y retención por inactividad (FR-034) con tareas programadas. `integration/identity/test_retention_tasks.py`, `test_erase_user.py`. |

## V13. API y servicios web

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 13.1.1 Mismos codificadores y analizadores | Cumple | JSON UTF-8 en todos los componentes. |
| 13.1.3 Sin información sensible en las URL de la API | Cumple (con nota) | Sin claves ni tokens en la URL; ver 8.3.1 sobre `?q=`. |
| 13.1.4 Autorización por URI y por recurso | Cumple | Permiso por ruta y comprobación de propiedad por recurso (V4.2.1). |
| 13.1.5 Rechazo de tipos de contenido inesperados | Cumple | Un cuerpo JSON enviado como `text/plain` recibe 422 (FastAPI 0.142, comprobado contra el stack el 2026-10-08); el lote exige `text/csv`. |
| 13.2.1 Solo métodos HTTP válidos | Cumple | Las rutas declaran su método; los demás reciben 405. |
| 13.2.2 Validación con esquema | Cumple | Pydantic y contrato OpenAPI; Schemathesis sin fallos (T177). |
| 13.2.3 Protección CSRF | Cumple | Ver 4.2.2. |
| 13.2.5 `Content-Type` verificado | Cumple | Ver 13.1.5. |
| 13.2.6 Cabeceras y cuerpo confiables | Cumple | HTTPS obligatorio fuera de localhost, HSTS, TLS 1.2 y 1.3 (`infra/nginx/tls.conf`). |
| 13.3.x SOAP, 13.4.x GraphQL | N/A | La API es REST/JSON. |

Sin CORS: no hay `CORSMiddleware`. La PWA y la API comparten origen detrás de Nginx, así que
otro origen no puede leer las respuestas.

---

## Hallazgos abiertos

Ninguno. Los tres de esta revisión se resolvieron el 2026-10-08: T178a (2.7.2), T178b (3.3.4) y
T178c (2.10.2).

## Desviaciones aceptadas

| Requisito | Motivo | Mitigación |
|-----------|--------|------------|
| 2.2.2, 2.7.1 | Invitados sin cuenta Unilibre (FR-007) | Rol sin privilegios, enlaces de un solo uso, vencimiento y revocación inmediata |
| 2.10.1 | Sin gestor de identidades de servicio | Contraseñas por rol desde el entorno, red interna, mínimo privilegio |
| 3.3.2 | Uso sin conexión de 7 días (FR-038) | Sesión privilegiada de 12 h / 30 min para funciones con datos de terceros (plan.md, Complexity Tracking) |
| 3.4.4 | `Path=/api/auth` incompatible con `__Host-` | Cookie *host-only*, `Secure`, `HttpOnly`, `SameSite=Strict` |
| 8.2.2 | Uso sin conexión (FR-038) | Instantánea mínima sin tokens, borrada al terminar la sesión |
| 4.3.1 | El MFA lo impone Entra ID | Pedido a TI (quickstart.md, sección 2) |
