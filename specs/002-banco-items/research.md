# Research: Banco de ítems (002)

Decisiones técnicas de la funcionalidad 002. La base del proyecto (stack, contextos, outbox,
sesiones, CI) está en [../001-identidad-acceso/research.md](../001-identidad-acceso/research.md);
aquí se citan sus decisiones como "001/R-NN". Cada dependencia nueva se justifica (principio XI).

Formato de cada decisión: **Decisión**, **Justificación**, **Alternativas descartadas**.

---

## R-01. Contexto `content` y su fachada

**Decisión**: el banco vive en un contexto delimitado nuevo, `saber_uli.content`, con las capas
`domain / application / infrastructure / api` y un esquema propio `content` en PostgreSQL. Expone
`content.application.public` como única fachada para otros contextos. En 002 la fachada no tiene
consumidores; la práctica (003) leerá de ella las versiones publicadas. `content` usa de
`identity.application.public` solo el usuario autenticado, los permisos y los nombres para mostrar
(R-14).

**Justificación**: el kit (sección 6) ya nombra el contexto `content`; el principio II exige
esquema por contexto y comunicación por fachadas. `import-linter` agrega `saber_uli.content` a los
contratos de capas, de dominio puro y de independencia.

**Alternativas descartadas**: ponerlo dentro de `identity` (mezcla dos lenguajes del dominio);
un servicio aparte (el principio II pide ADR con datos para microservicios y no los hay).

## R-02. Versiones inmutables y una versión abierta por ítem

**Decisión**:

- Un **ítem** tiene identificador técnico `uuidv7()` y código de negocio estable y único
  (`LC-0001`), como pide el kit.
- Cada cambio de contenido vive en una **versión** numerada (1, 2, 3…). Una versión Publicada o
  Retirada es inmutable; solo la versión **abierta** (Borrador o En revisión) se edita.
- Invariantes con índices únicos parciales: a lo sumo **una** versión Publicada y a lo sumo **una**
  abierta por ítem. Al aprobar la abierta, la Publicada anterior pasa a Retirada en la misma
  transacción (FR-015).
- Cada versión de ítem **fija** la versión de su contexto. Editar un contexto crea una versión
  nueva del contexto. Las versiones abiertas que lo usan pasan a la nueva versión. Para cada ítem
  Publicado sin versión abierta se crea una versión nueva, En revisión, que usa la nueva versión
  del contexto (FR-020).
- Las consignas de escritura son ítems de tipo `writing_prompt` en la misma tabla: comparten
  estados, versiones, revisión e importación.

**Justificación**: las respuestas (003) guardan el id de la versión respondida, así que la
historia nunca cambia (FR-017, SC-006). Los índices parciales hacen cumplir FR-011 en la base y no
solo en el código.

**Alternativas descartadas**: guardar solo el último contenido con una tabla de auditoría de
cambios (las respuestas históricas perderían la versión exacta); event sourcing completo
(complejidad sin necesidad: principio XI).

## R-03. Formato de intercambio v1 y su JSON Schema

**Decisión**: el formato de importación y exportación JSON es el de
`backend/seeds/banco_inicial_saber_uli.json` (`esquema_version: "1.0"`): `modulos`, `contextos`,
`items`, `consignas_escritura` y `rubricas`. Se define con modelos Pydantic en
`content/infrastructure/interchange/`. Desde ellos se genera
`backend/schemas/banco_items.schema.json` (JSON Schema 2020-12), que se versiona. Una prueba falla
si el archivo generado difiere del versionado. Así el esquema publicado para los docentes (y para
la generación con IA del kit, sección 8.2) nunca se desincroniza del código.

Reglas del formato que no estaban explícitas en el archivo:

- `id` del ítem es el código de negocio; `version` se ignora al importar (la asigna el sistema) y
  se escribe al exportar.
- `estado` y `origen` del archivo se respetan solo en la carga del banco inicial. Un ítem del banco
  inicial sin `origen` o con `banco_inicial` se guarda con origen `seed`; los que traen `ia`, con
  `ai`, y en ambos casos entran En revisión. En una importación
  el estado lo elige el docente (Borrador o En revisión) y el origen es `docente`, salvo que el
  archivo diga `ia` (FR-019: entonces entra En revisión).
- Un archivo exportado incluye `modulos` solo con las categorías que usan sus ítems y las rúbricas
  que usan sus consignas, para que se pueda reimportar en otra instalación.

**Justificación**: el kit pide un JSON Schema versionado del formato de intercambio. Generarlo
desde los mismos modelos que validan evita mantener dos definiciones. Pydantic ya es dependencia.

**Alternativas descartadas**: escribir el JSON Schema a mano y validar con la librería
`jsonschema` (dos fuentes de verdad y una dependencia nueva).

## R-04. Plantilla de hoja de cálculo en XLSX con openpyxl

**Decisión**:

- **Formato y librería**: la plantilla es un archivo `.xlsx` que la aplicación genera
  (`GET /content/import-template`). Se lee y escribe con **openpyxl**, junto con **defusedxml**,
  que openpyxl usa automáticamente si está instalado.
- **Alcance** (aclaración de la spec, FR-029): solo ítems de selección de LC, RC, CC e Inglés
  partes 2 a 7, una fila por ítem.
- **Hojas**:
  - `items`: código, módulo, parte, códigos de taxonomía, dificultad, código de contexto, título y
    texto del contexto, enunciado, opciones A a D con su texto y su retroalimentación, clave
    correcta y explicación. Al final, la columna opcional `contexto_subtipo` (agregada en T087:
    sin ella, reimportar un texto de Lectura crítica perdía su subtipo); una plantilla anterior
    sin esa columna se sigue leyendo.
  - `instrucciones`: explica cada columna.
  - `listas`: códigos válidos para las validaciones de celda.
- **Contextos compartidos**: varias filas con el mismo código de contexto lo comparten. El texto se
  toma de la primera fila; si otra fila trae un texto distinto, es un error.
- **Defensas**: antes de abrir el archivo se verifica:
  - el tamaño (máximo 10 MB);
  - que el contenido descomprimido no pase de 50 MB, para frenar bombas zip;
  - que sea un ZIP con `[Content_Types].xml`.

  Se abre en modo `read_only` y se ignoran fórmulas y macros (`data_only=True`; un `.xlsm` se
  rechaza).
- **Exportación**: la plantilla solo incluye los ítems que puede representar e informa cuántos
  quedaron fuera (FR-038).

**Justificación**: los textos de los ítems tienen saltos de línea, comillas, punto y coma y tildes.
En CSV eso falla con frecuencia en Excel con configuración regional es-CO, que usa `;` como
separador y no siempre lee UTF-8. XLSX conserva el texto tal cual. openpyxl es puro Python, maduro
y con licencia MIT; defusedxml evita ataques XML (XXE y billion laughs) en el XML interno del
XLSX. En 001 se eligió CSV para invitaciones (001/R-21), porque allí solo hay correos y fechas.

**Alternativas descartadas**: CSV (problemas de codificación y separador descritos); Google Sheets
o Microsoft Graph (integración externa innecesaria); pandas (dependencia pesada para leer filas).

## R-05. Importación en dos pasos, síncrona

**Decisión**:

1. `POST /content/imports` recibe el archivo (`multipart/form-data`).
   - Detecta el formato por la extensión y la firma (`.json` o `.xlsx`) y lo valida completo.
   - Guarda una **importación pendiente** con el resultado por ítem:
     - nuevo;
     - actualización, con sus diferencias;
     - sin cambios;
     - con error, con sus motivos.

     También guarda el contenido normalizado listo para aplicar.
   - Devuelve la vista previa.
2. `POST /content/imports/{id}/confirmation` aplica en **una transacción** los ítems válidos,
   con la declaración de originalidad (FR-034, FR-036).
   - Antes de aplicar, recalcula los conflictos: si otro cambio tocó un ítem después de la vista
     previa, ese ítem pasa a error `changed-since-preview` y se informa.

Detalles:

- **Vencimiento**: una importación pendiente vence a las 24 horas. Una tarea de Beat purga las
  vencidas.
- **Límites** (FR-037): 10 MB y 1 000 ítems por archivo, por encima del mínimo de 500 de la spec.
- **Limitación de peticiones**: 30 subidas por hora por usuario.
- **Dependencia nueva**: **python-multipart**, que FastAPI necesita para recibir archivos.

**Justificación**: SC-004 pide la vista previa de 500 ítems en menos de 30 s y SC-003 la
confirmación en menos de 60 s. Validar 500 ítems es trabajo de CPU de pocos segundos y aplicarlos
son inserciones por lote, así que se pueden hacer dentro de la petición. Es el mismo patrón de lotes
de invitaciones de 001 (validar, luego confirmar). La transacción única cumple "todos o ninguno".

**Alternativas descartadas**: procesar en Celery con sondeo del estado (más piezas sin necesidad
medida; se reconsidera si la medición de rendimiento lo pide); aplicar sin vista previa (lo
prohíbe la spec).

## R-06. Huella de contenido: cambios y duplicados

**Decisión**: dos huellas SHA-256 por versión.

- **`content_hash`**: se calcula sobre el JSON canónico del contenido (enunciado, opciones,
  retroalimentación, explicación, taxonomía, dificultad, clave y contexto), con claves ordenadas,
  Unicode NFC y sin espacios externos. Si coincide con la versión vigente, el resultado es "sin
  cambios" y no se crea versión (FR-035, SC-002, SC-008).
- **`fingerprint`**: se calcula sobre el texto normalizado del enunciado, de las opciones
  ordenadas y del texto del contexto. La normalización aplica NFKC, minúsculas, quita tildes y
  puntuación y colapsa espacios. Si coincide con la de otro ítem con distinto código (en el banco o
  en el mismo archivo), es duplicado (FR-032). Se indexa para búsqueda rápida.

**Justificación**: la igualdad exacta sobre la forma canónica hace deterministas las
reimportaciones. La huella normalizada atrapa copias con diferencias triviales sin entrar en
paráfrasis, que quedó fuera de alcance.

**Alternativas descartadas**: similitud difusa con trigramas (falsos positivos entre ítems de una
misma consigna, como los de Inglés parte 1; y la spec excluye la paráfrasis).

## R-07. Carga del banco inicial en cada despliegue

**Decisión**: comando idempotente `saber-uli content load-seed [--file …]`, que el servicio
`migrate` ejecuta después de Alembic.

- **Concurrencia**: toma un *advisory lock* de PostgreSQL, para que dos despliegues no carguen a
  la vez.
- **Validación**: valida todo el archivo; si hay errores, no aplica nada y termina con código
  distinto de cero (FR-023). Así `migrate` falla y el despliegue no arranca con un banco a medias.
- **Taxonomía y rúbricas**: agrega las categorías y rúbricas nuevas. No modifica las existentes,
  porque las mantiene el administrador (US9).
- **Ítems y contextos**:
  - Si el código es nuevo, se crea En revisión con el origen del archivo.
  - Si existe, se compara el `seed_hash` del archivo con el que se guardó en la última carga de
    ese ítem:
    - igual: no se toca, aunque los docentes lo hayan cambiado (FR-022);
    - distinto: se crea una versión nueva En revisión;
    - distinto y el ítem tiene una versión abierta hecha por personas: no se aplica y se lista
      para incorporarlo a mano (FR-022a).
- **Registro**: cada carga queda en `content.seed_loads` con el hash del archivo y un resumen.

**Justificación**: cumple la aclaración del banco inicial evolutivo y la Definición de Terminado
(`docker compose up` desde cero con el banco cargado). El `seed_hash` por ítem separa "cambió el
archivo" de "cambió un docente".

**Alternativas descartadas**: una migración de Alembic con los datos (mezcla esquema y contenido
y no permite cargas posteriores); una carga manual desde la interfaz (no cumple "al desplegar").

## R-08. Permisos de contenido y revisión

**Decisión**: tres permisos nuevos en `identity.domain.permissions` (y en el esquema
`Permission` del contrato de 001, como ampliación compatible):

| Permiso | Rol | Funciones |
|---------|-----|-----------|
| `content:author` | Docente, Administrador | listar, crear, editar, comentar, enviar a revisión, importar, exportar, cobertura, estadísticas |
| `content:review` | Administrador | aprobar, devolver, rechazar, retirar (FR-013) |
| `content:taxonomy_manage` | Administrador | taxonomía, rúbricas, distribución objetivo (FR-045) |

- **Sesión privilegiada**: todas las rutas de contenido, salvo `GET /content/media/{id}`, exigen
  sesión privilegiada (001/R-15), igual que las demás funciones de docente y administrador.
- **Autoaprobación** (FR-012): cada versión guarda su `author_id` y el conjunto
  `contributor_ids`, con todas las personas que la crearon o modificaron, incluidas las de una
  importación. La aprobación falla con 403 `self-approval-forbidden` si quien aprueba está en ese
  conjunto.
- **Confirmación del revisor** (FR-014): la aprobación exige en el cuerpo
  `confirms_alignment: true` y `confirms_originality: true`, que quedan en la historia.

**Justificación**: sigue el modelo de 001 (permisos por rol en código, 001/R-22). El rol
Administrador recibe todos los permisos.

**Alternativas descartadas**: un rol nuevo de revisor (la aclaración lo descartó).

## R-09. Ediciones simultáneas: bloqueo optimista

**Decisión**: cada ítem y cada contexto tienen un entero `revision`, que sube con cualquier
cambio de sus versiones (edición, envío, aprobación, devolución, retiro).

- `GET` devuelve `ETag: "<revision>"`.
- Toda modificación (`PUT /content/items/{id}/draft`, `PUT /content/contexts/{id}`) exige
  `If-Match`.
- Si no coincide, responde 412 `edit-conflict` con la versión actual en el cuerpo. La interfaz
  muestra las dos versiones y el docente decide (FR-027).
- Sin `If-Match`, responde 428 `precondition-required`.

**Justificación**: es el mecanismo estándar de HTTP (RFC 9110) y no necesita bloqueos que
expiren.

**Alternativas descartadas**: bloqueos de edición con vencimiento (quedan colgados si el navegador
se cierra); "gana el último" (lo prohíbe FR-027).

## R-10. Contenido enriquecido: Markdown seguro con tablas y fórmulas

**Decisión**:

- **Formato**: los textos se guardan en Markdown (`*_md`), como en el banco inicial. Este trae
  12 tablas GFM y 5 fórmulas entre `$…$`.
- **Render**: en la PWA se usa `react-markdown`, ya instalado, sin HTML crudo (`skipHtml`), con
  tres complementos nuevos:
  - **remark-gfm**, para las tablas;
  - **remark-math** y **rehype-katex** (KaTeX), para las fórmulas, con salida
    `htmlAndMathml` para que los lectores de pantalla lean la fórmula (WCAG 2.2).
- **Vista previa**: un componente compartido `ContentView` (en `src/shared/content/`) muestra la
  vista previa del docente. La práctica (003) lo reutilizará, así que la vista previa es fiel
  (FR-025).
- **Conteo de palabras** de Lectura crítica (FR-007): lo hace el dominio. Quita la sintaxis
  Markdown (marcas, separadores de tabla y URLs de enlaces) y cuenta secuencias de letras o
  números separadas por espacios o puntuación. Así 500 palabras se acepta y 501 no.

**Justificación**: el contenido existente ya usa estas construcciones. Sin HTML crudo no hay XSS
desde el contenido. KaTeX no ejecuta código y su CSS se sirve desde el mismo origen (CSP de 001).

**Alternativas descartadas**: un editor WYSIWYG con HTML (superficie de XSS y otra dependencia
grande); MathJax (más pesado para celulares de gama media); imágenes de fórmulas (no son
accesibles).

## R-11. Imágenes de contextos en PostgreSQL, saneadas

**Decisión**: las imágenes se suben con `POST /content/media` y se guardan en la tabla
`content.media` (`bytea`).

- **Formatos y tamaño**: solo PNG, JPEG o WebP, verificados por su firma, de máximo 1 MB y
  4 000 px por lado. SVG queda prohibido porque puede llevar scripts.
- **Saneamiento**: se re-codifican con **Pillow**. Eso quita los metadatos EXIF, que pueden
  incluir la ubicación del dispositivo, un dato personal (principio V), y neutraliza archivos mal
  formados.
- **Deduplicación**: se identifican por el SHA-256 del resultado, así que la misma imagen se
  guarda una sola vez.
- **Entrega**: `GET /content/media/{id}` la sirve a quien tiene `content:author`, y a los demás
  usuarios autenticados solo si la imagen está en un contexto usado por una versión Publicada o
  Retirada (las respuestas históricas de 003 la necesitan); si no, 404 (FR-046). Va con
  `Cache-Control: private, max-age=31536000, immutable`, para que la PWA pueda guardarla para el
  uso sin conexión en 003.
- **Texto alternativo**: es obligatorio (FR-009) y vive en la versión del contexto, no en la
  imagen.

**Justificación**: el banco tendrá decenas o pocos cientos de imágenes pequeñas. En la base quedan
dentro de las copias de seguridad y de las transacciones, sin otro volumen ni servicio
(principio X). Pillow es el estándar para imágenes en Python.

**Alternativas descartadas**: sistema de archivos con un volumen (otra pieza que respaldar y
sincronizar); almacenamiento de objetos tipo S3 (servicio externo innecesario a esta escala).

## R-12. Búsqueda y escala de 10 000 ítems

**Decisión**:

- **Listado**: usa paginación por página (como 001) con filtros indexados: módulo, estado,
  origen, dificultad, categoría de la taxonomía, señales de problema y "pendientes de revisión".
- **Búsqueda de texto**: usa una columna generada `tsvector` con la configuración `spanish` sobre
  el enunciado y la explicación, con índice GIN, más `ILIKE` sobre el código del ítem (índice
  `text_pattern_ops`) y el título del contexto. No requiere extensiones.
- **Cobertura**: se calcula con agregaciones SQL por categoría.
- **Exportación**: lee por bloques de 500 y escribe el archivo en flujo.
- **Prueba de escala**: una prueba de integración siembra 10 000 ítems y mide SC-009 y SC-010,
  con el mismo enfoque que 001/T176 (medición en serie y exigencia con una variable de entorno).

**Justificación**: 10 000 filas es poco para PostgreSQL con índices. El índice de texto completo
nativo evita la extensión `pg_trgm`.

**Alternativas descartadas**: un motor de búsqueda externo (innecesario a esta escala); `ILIKE`
sin índice (degrada con el volumen).

## R-13. Estadísticas por versión

**Decisión**:

- **Cálculo**: lo hace una función pura del dominio (`content.domain.statistics`). Recibe las
  **primeras** respuestas de cada estudiante a una versión: si acertó, la opción elegida y su
  "puntaje del resto", es decir, la proporción de acierto del estudiante en las primeras
  respuestas a otros ítems del mismo módulo. Devuelve:
  - número de respuestas;
  - porcentaje de acierto;
  - porcentaje por opción;
  - **índice de discriminación**: correlación punto-biserial corregida entre el acierto en el
    ítem y el puntaje del resto;
  - señales de problema de FR-043.
- **Mínimo de respuestas**: con menos de 30, el resultado es "datos insuficientes" (FR-042).
- **Datos de entrada**: las respuestas pertenecen a la práctica (003). `content` define el puerto
  `ResponseStatisticsSource`. En 002 su adaptador no devuelve datos; 003 lo implementa leyendo su
  propio esquema por su fachada.
- **Recálculo**: una tarea de Beat recalcula cada noche la tabla `content.item_version_stats`,
  que es la que permite filtrar por señales de problema y responder en menos de 2 s (SC-009).
- **Privacidad**: las estadísticas son agregadas (FR-044). El puerto entrega filas sin
  identificador del estudiante.

**Justificación**: la punto-biserial corregida es el índice de discriminación más usado en la
teoría clásica de los tests, y no depende del motor adaptativo (005). Separar la fórmula, que se
prueba ya, de la fuente de datos, que llega en 003, permite entregar US8 completa en interfaz y
contrato sin inventar respuestas.

**Alternativas descartadas**: índice de grupos extremos 27 % (descarta datos con pocas
respuestas); parámetros de TRI (requieren muchas más respuestas; ADR 0007 los deja para después).

## R-14. Historia y auditoría del contenido dentro del contexto

**Decisión**:

- **Historia de cada ítem**: `content.item_events` registra cada creación, edición, envío,
  aprobación, devolución, rechazo, retiro, comentario, importación y carga del banco inicial, con
  actor, fecha, versión, comentario o motivo, y detalles sin datos personales. Esta historia es la
  auditoría de los ítems (FR-018, FR-047).
- **Otros registros**: importaciones, exportaciones y cambios de taxonomía quedan en
  `content.imports`, `content.exports` y `content.taxonomy_changes`.
- **Solo agregar**: el rol de la aplicación tiene `INSERT` y `SELECT` sobre esas tablas, sin
  `UPDATE` ni `DELETE`, como la auditoría de 001 (V20).
- **Nombres de las personas**: no se copian. `content` guarda solo identificadores de usuario y
  pide los nombres a la fachada de `identity`, con un método nuevo
  `UserDirectory.display_names(ids)`. Una cuenta suprimida aparece como "Cuenta eliminada".
  Por eso `identity.UserErased` no requiere manejador en `content`.
- **Mis datos**: `content` registra un proveedor en `DataExportRegistry` con la sección
  `banco_de_items`, que lista los códigos de los ítems y versiones que la persona creó, modificó o
  revisó (FR-031 de 001).

**Justificación**: el principio II prohíbe escribir en las tablas de `identity`. Escribir la
auditoría en la misma transacción que la acción exige que viva en el mismo esquema. Guardar solo
identificadores minimiza los datos personales (principio V).

**Alternativas descartadas**: enviar eventos por el outbox para que `identity` los audite (la
auditoría deja de ser atómica con la acción y el catálogo cerrado de 001 tendría que conocer a
`content`); copiar el nombre del autor en cada versión (dato personal duplicado que habría que
borrar en cada supresión).

## R-15. Contrato propio de 002 y cliente generado

**Decisión**:

- **Archivo**: el contrato de esta funcionalidad es `specs/002-banco-items/contracts/openapi.yaml`
  (OpenAPI 3.1), autocontenido. Copia de 001 los componentes comunes (`Problem`, `PageMeta`, las
  respuestas de error y los parámetros de paginación), con nombres idénticos.
- **Cliente**: orval agrega un segundo destino (`src/api/content/`).
- **Pruebas de contrato**: Schemathesis agrega una suite que recorre este contrato.
- **Operaciones implementadas**: la comprobación de `main.py` usa la unión de los dos contratos.
- **Cambio en 001**: solo se agregan los tres permisos nuevos al enum `Permission`. Es una
  ampliación compatible, así que no cambia la versión `/api/v1` (principio III).

**Justificación**: un archivo por funcionalidad mantiene el vínculo spec → contrato y evita que el
contrato de 001 crezca sin límite. Las referencias `$ref` entre archivos complican orval y
Schemathesis, y duplicar cuatro esquemas pequeños es más barato.

**Alternativas descartadas**: un contrato único creciente (rompe la trazabilidad por
funcionalidad); `$ref` externos al contrato de 001 (generan modelos duplicados en orval).

## R-16. Cobertura frente a la distribución del examen

**Decisión**:

- **Objetivo**: cada categoría de la taxonomía puede tener un **peso objetivo** entre 0 y 1. El
  banco inicial trae `peso_aprox` en las afirmaciones de LC, en las competencias de RC y CC y en
  las partes de Inglés.
- **Cálculo**: la cobertura de un módulo agrupa por el tipo de categoría que tiene pesos: LC por
  afirmación, RC y CC por competencia e Inglés por parte. CE no tiene pesos y muestra solo totales.
  - En cada categoría muestra los ítems Publicados y En revisión, el porcentaje real sobre los
    publicados del módulo, el peso objetivo y el **faltante**: los ítems que harían falta para
    llegar al objetivo con la meta del kit de unos 150 por módulo y 225 en Inglés.
  - La meta por módulo es un dato del módulo que el administrador edita.
- **Indicación de faltantes**: las categorías bajo el objetivo se marcan con texto
  ("Faltan N"), además del color, como pide FR-039.

**Justificación**: usa los datos que ya trae el banco inicial y la meta del kit. Ser datos
configurables cumple FR-040.

**Alternativas descartadas**: porcentajes fijos en el código (lo prohíbe FR-001).

## R-17. Interfaz del banco en la PWA

**Decisión**:

- **Ubicación**: una funcionalidad nueva `src/features/content/` con rutas bajo `/banco` y la
  pantalla de taxonomía en `/admin/taxonomia`. Todas se cargan bajo demanda, como en 001/T174.
- **Rutas**:
  - `/banco`: lista y filtros;
  - `/banco/revision`: cola de revisión de los administradores;
  - `/banco/items/nuevo` y `/banco/items/$code`: editor con vista previa e historial;
  - `/banco/contextos/$code`;
  - `/banco/importar` y `/banco/importaciones/$importId`;
  - `/banco/exportar`;
  - `/banco/cobertura`.
- **Formularios**: usan react-hook-form y zod con las mismas reglas que el dominio. Los errores
  del servidor (`errors[]` de Problem Details) se muestran junto a cada campo.
- **Vista previa** (FR-025): `ContentView` se muestra dentro de un marco de 360 × 800 px, que
  imita un celular de gama media, y una pestaña "Retroalimentación" muestra la de cada opción.
- **Uso sin conexión**: estas pantallas son de gestión; necesitan conexión y lo dicen. Solo el
  `ContentView` se reutilizará sin conexión en 003.

**Justificación**: sigue la organización por funcionalidades de 001 y su accesibilidad (axe en
CI).

**Alternativas descartadas**: una aplicación de administración aparte (otra base de código para el
mismo equipo).

## R-18. Ritmo de implementación y pruebas de rendimiento

**Decisión**: las metas SC-003, SC-004, SC-009 y SC-010 se prueban en integración con
PostgreSQL real.

- **Datos**: 500 ítems para la importación y 10 000 para listados, cobertura y exportación.
- **Exigencia**: con `PERF_BUDGETS_ENFORCE=1`; sin la variable, solo se miden y se registran, como
  en 001/T176.
- **Lugar de medición**: la medición definitiva se hace en el servidor de referencia, junto con
  la pendiente de 001.

**Justificación**: en CI los runners compartidos dan tiempos variables; medir siempre y exigir
donde el entorno es estable evita pruebas intermitentes.

**Alternativas descartadas**: exigir las metas en CI (falsos negativos por carga de los runners).

---

## Dependencias nuevas

| Dependencia | Dónde | Para qué | Decisión |
|-------------|-------|----------|----------|
| python-multipart | backend | Recibir archivos en FastAPI (importación, imágenes) | R-05 |
| openpyxl | backend | Leer y escribir la plantilla XLSX | R-04 |
| defusedxml | backend | Proteger openpyxl de ataques XML | R-04 |
| Pillow | backend | Validar y re-codificar imágenes, quitar EXIF | R-11 |
| remark-gfm | frontend | Tablas en el contenido | R-10 |
| remark-math, rehype-katex (KaTeX) | frontend | Fórmulas accesibles | R-10 |

Todas tienen licencias permisivas (MIT, BSD o HPND) y mantenimiento activo. Dependabot y Trivy
las vigilan desde 001.
