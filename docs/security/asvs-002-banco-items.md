# Verificación OWASP ASVS 4.0.3 nivel 2: 002 Banco de ítems

**Tarea**: T115 | **Fecha**: 2026-10-10 | **Revisó**: Opus | **Base**: revisiones de US1 a US9
(T040 a T108) y pruebas automáticas de 002.

Alcance: el contexto `content` de la API (`backend/src/saber_uli/content`), sus pantallas en la
PWA (`frontend/src/features/content`, `frontend/src/shared/content`) y el proxy Nginx
(`infra/nginx`) en lo que toca al banco. Capítulos pedidos por la tarea: V4, V5, V7, V12 y V13.
La autenticación, las sesiones y la sesión privilegiada son las de 001
([`asvs-001-identidad.md`](asvs-001-identidad.md)) y no se repiten.

Estados: **Cumple** (con evidencia), **Desviación** (decisión registrada con mitigación),
**Hallazgo** (no cumplía; se indica la corrección o el plan) y **N/A** (con el motivo). Las rutas
de pruebas son relativas a `backend/tests/` salvo que empiecen por `frontend/`.

---

## V4. Control de acceso

Modelo: tres permisos (`content:author` para docentes y administradores, `content:review` y
`content:taxonomy_manage` para administradores; research R-08), todos con sesión privilegiada.
La regla de negocio central es que nadie aprueba lo que creó o modificó (FR-012).

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 4.1.1 Control en el servidor | Cumple | Cada ruta declara su permiso con `privileged_with(...)` (`content/api/dependencies.py`); la PWA solo oculta lo que no aplica. `integration/content/test_content_access.py::test_reglas_de_acceso_de_cada_operacion_implementada` recorre las 35 operaciones del contrato con estudiante, docente y administrador. |
| 4.1.2 Atributos no manipulables por el usuario | Cumple | Permisos y roles vienen del token firmado y de la base (001); el autor, el revisor y quien importa salen de la sesión, nunca del cuerpo. |
| 4.1.3 Mínimo privilegio | Cumple | Docente: crear, editar, comentar, importar y exportar; revisar y mantener la taxonomía, solo administración. Un estudiante solo ve imágenes de contenido publicado. `integration/content/test_media.py::test_un_estudiante_solo_ve_imagenes_de_contenido_publicado`, `test_taxonomy_admin.py::test_un_docente_no_cambia_la_taxonomia`. |
| 4.1.5 Falla cerrada | Cumple | Sin permiso, 403 antes de tocar datos; sin sesión privilegiada, 401 `reauthentication-required`. |
| 4.2.1 Acceso a objetos (IDOR) | Cumple | Una importación la ve y la confirma solo quien la subió (quien revisa ve todas, sin confirmar); un id ajeno responde 404. `integration/content/test_import_api.py::test_cada_docente_ve_sus_importaciones_y_el_administrador_todas`. Los ítems y contextos son del banco compartido (FR-008), no de una persona. |
| 4.2.2 Protección contra CSRF | Cumple | La API usa `Authorization: Bearer` y `X-Requested-With` (001, V4.2.2); ninguna operación del banco depende de cookies. |
| 4.3.1 MFA para administración | Cumple (001) | Heredado: la sesión privilegiada y el MFA de Entra ID (ver 001, V4.3.1). |
| 4.3.2 Sin listado de directorios ni metadatos expuestos | Cumple | Las imágenes se sirven por id desde la base, no desde un directorio; Nginx no lista directorios. |
| 4.3.3 Reautenticación para operaciones sensibles | Cumple | Todas las rutas de `content` exigen sesión privilegiada (R-08). |
| Regla de negocio: autoaprobación (FR-012) | Cumple | El dominio rechaza que apruebe quien es autor o contribuyente de la versión, también si llegó por importación o por la propagación de un contexto. `integration/content/test_review.py::test_nadie_aprueba_lo_que_creo_o_modifico`, `test_items_api_review.py::test_la_autoaprobacion_se_ve_en_can_y_se_rechaza`, `test_bank_import_update.py::test_lo_abierto_se_actualiza_en_su_lugar`. |
| Regla de negocio: concurrencia | Cumple | Editar y revisar exigen `If-Match` (428 si falta, 412 con el ítem actual si cambió; R-09). `integration/content/test_items_api_review.py::test_sin_if_match_o_con_otra_revision`. |

## V5. Validación, desinfección y codificación

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 5.1.1 Contaminación de parámetros | Cumple | Un parámetro de consulta no declarado es 422 (`reject_unknown_query`), no se ignora. |
| 5.1.2 Asignación masiva | Cumple | Los cuerpos son modelos Pydantic con `extra="forbid"`; `id`, autor, estado y revisión nunca vienen del cliente. |
| 5.1.3 Validación positiva | Cumple | Listas cerradas (módulo, estado, dificultad, tipo), patrones de código (`^[A-Z]{2,3}(-[A-Z0-9]+){1,3}$`), longitudes y reglas por módulo del dominio (FR-024; `content/domain/validation.py`). Los booleanos de la taxonomía son estrictos (`StrictBool`). |
| 5.1.4 Datos estructurados | Cumple | El formato de intercambio se valida con los mismos modelos que generan `backend/schemas/banco_items.schema.json` (R-03). Hallazgo H1 (corregido): los códigos de ítems y contextos de un archivo no seguían el formato de la API (ver abajo). |
| 5.1.5 Redirecciones | N/A | El banco no redirige a URL externas. |
| 5.2.1 HTML del usuario | Cumple | Los textos son Markdown. `MarkdownView` usa `react-markdown` con `skipHtml` y sin `rehype-raw`: el HTML crudo se descarta y nada se ejecuta (`frontend/src/shared/content/MarkdownView.tsx`; `frontend/src/shared/content/ContentView.test.tsx`). |
| 5.2.6 SSRF | N/A | El servidor no descarga nada de URL que dé el usuario; las imágenes se suben como archivo. |
| 5.2.7 SVG | Cumple | Solo PNG, JPEG y WebP, decididos por el contenido (Pillow), no por la extensión. `integration/content/test_media.py::test_rechaza_lo_que_no_es_png_jpeg_ni_webp`. |
| 5.3.1 Codificación de salida según el contexto | Cumple | React escapa el texto; JSON con el serializador de FastAPI. Hallazgo H2 (corregido): en el reporte de errores XLSX, un código o mensaje que empezaba por `=` se escribía como fórmula. Las exportaciones y la plantilla ya escribían esos textos como cadena. |
| 5.3.3 XSS | Cumple | Sin `dangerouslySetInnerHTML` en `content`; los enlaces de Markdown pasan por la transformación de URL de `react-markdown` (descarta `javascript:`) y abren con `rel="noopener noreferrer"`; CSP `script-src 'self'` e `img-src 'self' data: blob:` (`infra/nginx/security-headers.conf`) impide cargar imágenes o scripts externos desde un enunciado. |
| 5.3.4, 5.3.5 Inyección SQL | Cumple | SQLAlchemy con parámetros; la búsqueda escapa `%` y `_` (`contains_pattern`) y quita el carácter NUL. `integration/content/test_items_api_review.py::test_la_busqueda_resiste_nul_y_paginas_enormes`. Los textos con NUL o sustitutos UTF-16 sueltos responden 422 en vez de un 500 de PostgreSQL (US9). |
| 5.5.1, 5.5.3 Deserialización | Cumple | JSON con `json.loads` (sin objetos) y anidación excesiva rechazada; XLSX con openpyxl sobre defusedxml, sin evaluar fórmulas. `unit/content/test_xlsx.py::test_el_xml_con_entidades_externas_se_rechaza`, `test_las_formulas_se_leen_como_texto`. |

## V7. Registro de errores y auditoría

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 7.1.1, 7.1.2 Sin credenciales ni datos personales en los logs | Cumple | Los logs del banco llevan códigos, identificadores y conteos (principio V; R-14). `integration/content/test_content_logs.py` (T113) recorre la carga, la importación con un nombre de archivo único, la revisión con comentario y motivo, un 422 y la exportación, a nivel DEBUG, y no encuentra nombres, correos, textos, comentarios, motivos ni nombres de archivo. `integration/content/test_cli_load_seed.py`. |
| 7.1.3 Eventos de seguridad registrados | Cumple | La historia del ítem (`content.item_events`, solo inserción) registra creación, edición, envío, aprobación con las dos confirmaciones (FR-014), devolución, rechazo, retiro, comentarios, importación y carga del banco inicial; la taxonomía, en `content.taxonomy_changes` con el antes y el después; importaciones y exportaciones en sus tablas. |
| 7.1.4 Información suficiente | Cumple | Cada evento lleva actor (UUID), fecha, versión y el detalle sin contenido; los nombres los da `identity` al mostrarlos (R-14). |
| 7.2.1, 7.2.2 Auditoría a prueba de cambios | Cumple | `saber_app` solo inserta en `item_events`, `taxonomy_changes`, `exports` y `seed_loads`, y solo cambia el estado y el resultado de `imports` (permisos de columna). `integration/content/test_db_grants.py::test_tablas_de_solo_insercion`, `test_de_una_importacion_solo_cambian_el_estado_y_el_resultado`. |
| 7.3.x Protección de los logs | Cumple (001) | Salida JSON a stdout recogida por Docker (001, V7.3). |
| 7.4.1 Mensajes de error genéricos | Cumple | `application/problem+json` con slug, sin trazas; los 500 no revelan detalles (001). |

## V12. Archivos y recursos

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 12.1.1 Tamaño máximo | Cumple | Importación: se leen como máximo 10 MB + 1 byte (`transfer_router.py`), y Nginx admite hasta 11 MB solo en `POST /api/v1/content/imports` (el resto de la API, 2 MB). Imágenes: 1 MB (413). Hallazgo H3 (corregido): Nginx cortaba en 2 MB las importaciones de 2 a 10 MB. `integration/content/test_import_api.py::test_rechazos_del_archivo`, `test_media.py::test_mas_de_un_mega_es_413`. |
| 12.1.2 Archivos comprimidos | Cumple | Antes de abrir un XLSX: ZIP con `[Content_Types].xml`, sin macros (un `.xlsm` se rechaza) y como máximo 50 MB descomprimidos (contra bombas zip). `unit/content/test_xlsx.py::test_defensas_antes_de_abrir`. |
| 12.1.3 Cuota por usuario | Cumple | 30 importaciones y 60 imágenes por hora por persona, con 429 y `Retry-After`; un archivo admite hasta 1 000 ítems (413 `batch-too-large`). `test_import_api.py::test_limite_de_30_subidas_por_hora`, `test_media.py::test_limite_de_60_subidas_por_hora_por_usuario`. |
| 12.2.1 Tipo de archivo verificado por el contenido | Cumple | Imágenes: Pillow decide el formato y re-codifica sin metadatos (EXIF fuera, también la ubicación); dimensiones revisadas antes de decodificar (4 000 px por lado). `test_media.py::test_quita_los_metadatos_exif`, `test_mas_de_4000_px_por_lado_es_415`. Importación: `.json` o `.xlsx`, leídos por su estructura. |
| 12.3.1 a 12.3.6 Nombres y rutas | Cumple | Nada se guarda en disco: imágenes y archivos van a la base por su id. El nombre de un archivo importado solo se guarda (sin ruta) para mostrarlo a quien lo subió; nunca entra a los logs ni a «Mis datos». |
| 12.4.1, 12.4.2 Almacenamiento fuera de la raíz web y antivirus | Desviación | No hay raíz web de archivos: las imágenes se sirven desde la base por la API. No hay antivirus: las imágenes se re-codifican (lo que descarta contenido ajeno al formato) y los archivos de importación nunca se sirven de vuelta. |
| 12.5.1, 12.5.2 Descargas | Cumple | Las imágenes salen con su `Content-Type` real y `X-Content-Type-Options: nosniff`; plantillas, reportes y exportaciones con `Content-Disposition: attachment`. |
| 12.6.1 SSRF por recursos | N/A | El servidor no pide recursos a URL del usuario. |

## V13. API y servicios web

| Req. | Estado | Evidencia o justificación |
|------|--------|---------------------------|
| 13.1.1 Codificación consistente | Cumple | JSON UTF-8; los archivos de intercambio en UTF-8 (con o sin BOM). |
| 13.1.3 Sin información sensible en la URL | Cumple | Las URL llevan códigos de negocio e ids; los textos y archivos van en el cuerpo. Los logs de petición no guardan la consulta. |
| 13.1.4 Autorización por recurso y operación | Cumple | Ver V4.1.1. |
| 13.1.5 Rechazo de tipos de contenido inesperados | Cumple | Cuerpos JSON validados por Pydantic; subidas `multipart/form-data` (415 o 422 si no corresponde). |
| 13.2.1 Métodos HTTP | Cumple | Solo los del contrato; la suite comprueba las 35 operaciones y que no haya rutas fuera del contrato. `contract/test_content_contract.py::test_ninguna_ruta_de_content_queda_fuera_del_contrato`. |
| 13.2.2 Validación con esquema | Cumple | `specs/002-banco-items/contracts/openapi.yaml` y Schemathesis sobre la app completa (T112), en verde. |
| 13.2.3 CSRF en API con cookies | Cumple (001) | Ver V4.2.2. |
| 13.2.5 `Content-Type` del pedido | Cumple | FastAPI exige el tipo declarado. |
| 13.2.6 Mensajes de error | Cumple | Problem Details con slugs del contrato (`taxonomy-node-in-use`, `edit-conflict`, `import-not-pending`…). |

---

## Hallazgos

| Id | Descripción | Estado |
|----|-------------|--------|
| H1 | Una importación aceptaba códigos de ítem o contexto con cualquier texto de hasta 32 caracteres. El ítem quedaba en el banco con un código que la API no puede abrir (la ruta exige el formato), y ese texto podía llegar a una hoja de cálculo. | Corregido (T115): los modelos del formato exigen el patrón de código de la API (`content/infrastructure/interchange/models.py`); JSON Schema regenerado. `unit/content/test_interchange.py::test_un_codigo_fuera_del_formato_es_un_error_de_la_entrada`. |
| H2 | Inyección de fórmulas en el reporte de errores XLSX: un código o mensaje que empezaba por `=` llegaba como fórmula al abrir el archivo. | Corregido (T115): `write_report` y las listas de la plantilla escriben esos textos como cadena (`_as_text` en `xlsx_format.py`). `unit/content/test_xlsx.py::test_el_reporte_escribe_como_texto_lo_que_empieza_por_igual`. |
| H3 | Nginx limitaba a 2 MB los cuerpos de toda la API: detrás del proxy, una importación de 2 a 10 MB fallaba con 413 (FR-037). | Corregido (T115): ubicación anidada con 11 MB solo para `POST /api/v1/content/imports` (`infra/nginx/locations.conf`); comprobado con `nginx -t` y una subida de 3 MB (llega a la API) frente a otra ruta (413). |
| O1 | `exportItems` no tiene límite de peticiones. Exportar las 10 000 preguntas tarda ~1 s (T110) y exige `content:author` con sesión privilegiada, así que el riesgo es bajo. | Decisión pendiente: si hace falta, un límite por persona (por ejemplo 30 por hora) requiere agregar 429 al contrato de `exportItems`. |

Sin hallazgos abiertos.
