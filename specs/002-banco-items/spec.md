# Feature Specification: Banco de ítems: carga inicial, importación, actualización y revisión

**Feature Branch**: `002-banco-items`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Usa la especificación 002 de la sección 4 de
@docs/SABER_ULI_KIT_SDD.md" (banco de ítems alineado a la estructura del ICFES, con carga
inicial, importación masiva, actualización, versionado y flujo de revisión).

## Contexto

La calidad del aprendizaje en Saber Uli depende de preguntas bien construidas, con
retroalimentación explicativa y trazables a lo que evalúa el ICFES. Esta funcionalidad define el
banco de ítems: qué es un ítem y un contexto, cómo se etiquetan frente a la estructura del examen,
cómo entran al banco (carga inicial, creación manual e importación en lote), cómo cambian sin
perder la historia (versiones) y cómo llegan a los estudiantes solo después de una revisión
humana. La práctica de los estudiantes (003) consume los ítems publicados; esta funcionalidad no
la incluye.

**Actores** (roles definidos en 001)

- **Docente**: crea, edita, importa y exporta ítems, los envía a revisión y consulta la
  cobertura y las estadísticas del banco.
- **Administrador**: además de lo anterior, revisa (aprueba, devuelve o rechaza) y retira
  ítems, carga el banco inicial y mantiene la taxonomía (módulos, competencias, afirmaciones,
  evidencias, componentes, situaciones, tipos de texto, partes de Inglés y rúbricas).
- **Estudiante e Invitado**: solo reciben ítems publicados, a través de la práctica (003).

**Vocabulario**

- **Ítem**: pregunta de selección (única respuesta o emparejamiento) con sus opciones,
  retroalimentación por opción y explicación general.
- **Consigna**: tarea abierta de Comunicación escrita, asociada a una rúbrica y a una condición de
  pertinencia. En lo que sigue, "ítem" incluye las consignas salvo que se diga lo contrario.
- **Contexto**: material que comparten uno o varios ítems: texto, tabla, imagen o lista de
  opciones compartidas (por ejemplo, las 8 palabras de la parte 1 de Inglés).
- **Taxonomía**: clasificación de cada módulo según la guía del ICFES: competencias, afirmaciones
  y evidencias, y además componente y tipo de situación (Razonamiento cuantitativo), tipo de texto
  (Lectura crítica) o parte (Inglés).
- **Versión**: estado del contenido de un ítem en un momento dado. Un ítem conserva su
  identificador estable a través de sus versiones.

## Clarifications

### Session 2026-10-08

- Q: ¿Quién puede aprobar, devolver o rechazar ítems en revisión? → A: Solo los
  administradores; los docentes crean, editan, importan y envían a revisión. Nadie aprueba una
  versión que creó o modificó, tampoco un administrador.
- Q: ¿Qué cubre la plantilla de hoja de cálculo? → A: Solo ítems de selección con su contexto de
  texto, una fila por ítem. Inglés parte 1 (opciones compartidas), los contextos con imagen o
  tabla y las consignas de escritura se importan con el formato del banco inicial.
- Q: ¿Quién puede editar un ítem que otra persona creó? → A: Cualquier docente edita cualquier
  ítem; cada cambio queda registrado con su autor y pasa por revisión.
- Q: Si una versión futura de la aplicación trae un banco inicial con ítems nuevos o corregidos,
  ¿qué pasa al desplegarla sobre un banco existente? → A: Se agregan los ítems con identificador
  nuevo (En revisión); los que cambiaron en el archivo crean una versión nueva En revisión; los
  que no cambiaron se ignoran.
- Q: ¿Hasta cuántos ítems debe manejar el banco sin perder agilidad? → A: Hasta 10 000 ítems, con
  búsquedas y filtros que respondan en menos de 2 segundos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Carga del banco inicial (Priority: P1)

Como administrador quiero que el banco inicial incluido en el proyecto (43 ítems, 3 consignas,
8 contextos, la taxonomía de los cinco módulos y la rúbrica de escritura) se cargue al desplegar
por primera vez, sin duplicar nada si la carga se repite, y que las versiones futuras de la
aplicación puedan traer ítems nuevos o corregidos sin pisar el trabajo de los docentes.

**Why this priority**: sin banco no hay práctica; es la base de todas las demás historias y la
Definición de Terminado de la constitución exige esta carga a partir de 002.

**Independent Test**: desplegar desde cero y verificar que el banco tiene 43 ítems, 3 consignas y
8 contextos en estado En revisión con origen "ia"; repetir la carga y verificar que los conteos
no cambian.

**Acceptance Scenarios**:

1. **Given** un despliegue nuevo sin ítems,
   **When** se completa la carga inicial,
   **Then** el banco contiene los 43 ítems, las 3 consignas y los 8 contextos del archivo, en
   estado En revisión, con su origen marcado, y la taxonomía y la rúbrica quedan disponibles.
2. **Given** un banco ya cargado y el mismo archivo,
   **When** la carga inicial se ejecuta otra vez,
   **Then** no se crean ítems, contextos ni versiones nuevos y se informa que no había cambios.
3. **Given** un ítem del banco inicial que un docente ya editó o publicó y que no cambió en el
   archivo,
   **When** la carga se repite,
   **Then** el ítem conserva el trabajo del docente; la carga no lo toca.
4. **Given** una versión nueva de la aplicación cuyo archivo trae ítems con identificador nuevo,
   **When** se despliega,
   **Then** esos ítems entran En revisión con su origen, y el resultado informa cuántos se
   agregaron.
5. **Given** un ítem cuyo contenido cambió en el archivo desde la última carga,
   **When** se despliega,
   **Then** se crea una versión nueva En revisión; la versión publicada, si la hay, sigue
   entregándose hasta que la nueva se apruebe.
6. **Given** un ítem que cambió en el archivo y que además tiene una versión en Borrador o En
   revisión hecha por un docente,
   **When** se despliega,
   **Then** el cambio del archivo no se aplica a ese ítem y queda en el resultado de la carga para
   que un docente lo incorpore a mano.
7. **Given** un archivo de banco inicial con un error de validación,
   **When** se intenta la carga,
   **Then** no se carga nada y el error identifica el elemento y la regla incumplida.

---

### User Story 2 - Revisión y publicación (Priority: P1)

Como administrador quiero aprobar, devolver con comentarios o rechazar los ítems En revisión, y
retirar los publicados, para que solo lleguen a los estudiantes ítems revisados por una persona
distinta de su autor.

**Why this priority**: el banco inicial entra En revisión; sin este flujo ningún ítem llega a
publicarse y la constitución (VI) exige revisión humana antes de publicar.

**Independent Test**: un docente envía un ítem a revisión y un administrador lo aprueba;
verificar que pasa a Publicado, que un docente no puede aprobar y que un administrador no puede
aprobar un ítem que él mismo modificó.

**Acceptance Scenarios**:

1. **Given** un ítem En revisión creado por otra persona,
   **When** un administrador lo aprueba,
   **Then** pasa a Publicado, queda disponible para la práctica y se registra quién lo aprobó y
   cuándo.
2. **Given** un ítem En revisión,
   **When** el administrador lo devuelve con comentarios,
   **Then** vuelve a Borrador con los comentarios visibles para el autor, y el autor puede
   corregirlo y enviarlo otra vez a revisión.
3. **Given** un ítem En revisión,
   **When** el administrador lo rechaza indicando el motivo,
   **Then** pasa a Retirado sin haber sido publicado y el motivo queda registrado.
4. **Given** un administrador que creó o modificó la versión En revisión de un ítem,
   **When** intenta aprobarla,
   **Then** el sistema lo impide e indica que la debe aprobar otro administrador.
5. **Given** un ítem publicado,
   **When** un administrador lo retira indicando el motivo,
   **Then** deja de entregarse en la práctica nueva y las respuestas ya dadas conservan la versión
   respondida.
6. **Given** un ítem del banco inicial (origen "ia"),
   **When** se muestra a un administrador para revisarlo,
   **Then** se ve su origen y se le pide confirmar que lo verificó contra la guía del ICFES y que
   no reproduce preguntas del ICFES antes de aprobar.
7. **Given** un docente sin rol Administrador y un ítem En revisión,
   **When** intenta aprobarlo, devolverlo o rechazarlo,
   **Then** se le niega la acción; puede comentar el ítem, pero no decidir.

---

### User Story 3 - Crear, editar y previsualizar ítems y contextos (Priority: P1)

Como docente quiero crear y editar ítems, consignas y contextos con formularios que validen las
reglas del módulo, y previsualizarlos tal como los verá el estudiante en el celular.

**Why this priority**: es el camino básico para corregir el banco inicial durante la revisión y
para que crezca; la importación en lote se apoya en las mismas reglas.

**Independent Test**: crear un ítem de Razonamiento cuantitativo con su contexto, previsualizarlo
en vista de celular, enviarlo a revisión y verificar que se aplicaron las validaciones.

**Acceptance Scenarios**:

1. **Given** un docente,
   **When** crea un ítem de Lectura crítica con 4 opciones, una correcta, retroalimentación en cada
   opción, explicación general y taxonomía completa,
   **Then** el ítem se guarda en Borrador con él como autor.
2. **Given** un ítem en edición,
   **When** falta la retroalimentación de una opción, hay cero o más de una opción correcta, el
   número de opciones no corresponde al módulo o a la parte, o un código de taxonomía no existe,
   **Then** no se puede enviar a revisión y cada problema se señala junto al campo.
3. **Given** un contexto de Lectura crítica,
   **When** su texto supera 500 palabras,
   **Then** no se puede guardar y se muestra el conteo actual frente al máximo.
4. **Given** un ítem con su contexto,
   **When** el docente abre la vista previa,
   **Then** lo ve como en el celular del estudiante: contexto, enunciado y opciones, y por cada
   opción la retroalimentación que se mostraría al elegirla.
5. **Given** un contexto compartido por varios ítems,
   **When** el docente lo edita,
   **Then** ve cuántos ítems lo usan y cuáles están publicados antes de confirmar.
6. **Given** un ítem publicado,
   **When** un docente lo edita,
   **Then** se crea una versión nueva en Borrador; la versión publicada sigue entregándose hasta
   que la nueva se apruebe.
7. **Given** una imagen en un contexto,
   **When** el docente la agrega,
   **Then** debe escribir su texto alternativo; sin él no se puede enviar a revisión.

---

### User Story 4 - Importación de ítems nuevos en lote (Priority: P2)

Como docente quiero importar ítems nuevos desde un archivo con el mismo formato del banco inicial
o desde una plantilla de hoja de cálculo, ver una vista previa y un reporte de errores por ítem
antes de confirmar.

**Why this priority**: permite crecer el banco a la escala necesaria (el examen tiene 135
preguntas de selección), pero el banco ya es útil con la creación manual.

**Independent Test**: importar un archivo con 20 ítems válidos y 3 inválidos; verificar la vista
previa, el reporte de errores y que al confirmar solo entran los válidos.

**Acceptance Scenarios**:

1. **Given** un archivo válido en el formato del banco inicial,
   **When** el docente lo sube,
   **Then** ve una vista previa con cuántos ítems, consignas y contextos son nuevos, cuántos
   actualizan algo existente y cuántos tienen errores, antes de que se guarde nada.
2. **Given** un archivo con ítems inválidos,
   **When** se valida,
   **Then** el reporte indica, por cada ítem con problemas, su identificador, el campo y la regla
   incumplida, y el docente puede descargar ese reporte.
3. **Given** la vista previa de una importación con errores,
   **When** el docente confirma,
   **Then** entran solo los ítems válidos, en Borrador o En revisión según elija, y los inválidos
   quedan fuera con su motivo.
4. **Given** la plantilla de hoja de cálculo descargada desde la aplicación,
   **When** el docente la llena con ítems de selección (una fila por ítem, con su contexto de
   texto) y la sube,
   **Then** se valida con las mismas reglas que el formato del banco inicial.
5. **Given** una plantilla con un ítem de Inglés parte 1, un contexto con imagen o tabla, o una
   consigna de escritura,
   **When** se valida,
   **Then** ese ítem se marca con error indicando que debe importarse con el formato del banco
   inicial.
6. **Given** un ítem del archivo cuyo contenido coincide con otro ítem del banco que tiene un
   identificador distinto,
   **When** se valida,
   **Then** se marca como duplicado y no se importa.
7. **Given** un docente que importa,
   **When** confirma la importación,
   **Then** declara que los ítems son originales y no reproducen preguntas del ICFES, y la
   declaración queda registrada con la importación.

---

### User Story 5 - Actualización de ítems en lote con versiones (Priority: P2)

Como docente quiero actualizar ítems existentes en lote: si el identificador ya existe, el
sistema crea una nueva versión en lugar de duplicarlo y me muestra qué cambió.

**Why this priority**: permite corregir muchos ítems a la vez tras una revisión o una nueva guía
del ICFES, sin perder la historia; depende de la importación (US4).

**Independent Test**: exportar 10 ítems publicados, cambiar el enunciado de 3, reimportar y
verificar que solo esos 3 tienen una versión nueva, con sus diferencias, y que reimportar el mismo
archivo no crea nada.

**Acceptance Scenarios**:

1. **Given** un archivo con ítems cuyo identificador ya existe y cuyo contenido cambió,
   **When** el docente ve la vista previa,
   **Then** cada uno muestra las diferencias campo por campo frente a su versión vigente.
2. **Given** la confirmación de esa importación,
   **When** el ítem existente está Publicado,
   **Then** se crea una versión nueva que entra a revisión, y la publicada sigue entregándose
   hasta que la nueva se apruebe.
3. **Given** un ítem existente en Borrador o En revisión,
   **When** se reimporta con cambios,
   **Then** se actualiza su versión en curso sin crear otra, y si estaba En revisión vuelve a
   Borrador o a revisión según elija el docente.
4. **Given** un archivo idéntico a uno ya importado,
   **When** se importa otra vez,
   **Then** la vista previa indica que no hay cambios y no se crean ítems ni versiones.
5. **Given** un ítem Retirado,
   **When** se reimporta con su identificador,
   **Then** se crea una versión nueva en Borrador o En revisión, y el historial conserva la
   retirada.
6. **Given** un ítem con varias versiones,
   **When** un docente abre su historial,
   **Then** ve cada versión con su estado, autor, revisor, fechas y diferencias frente a la
   anterior.

---

### User Story 6 - Exportación del banco (Priority: P2)

Como docente quiero exportar el banco completo o un filtro (por módulo, estado, origen, taxonomía
o dificultad) en el mismo formato de importación.

**Why this priority**: cierra el ciclo de actualización en lote y permite revisar el banco fuera
de la aplicación; depende del formato definido en US4.

**Independent Test**: exportar los ítems publicados de Inglés parte 1 y reimportar el archivo sin
cambios; verificar que la vista previa no muestra cambios.

**Acceptance Scenarios**:

1. **Given** un filtro,
   **When** el docente exporta,
   **Then** recibe un archivo con los ítems que cumplen el filtro, su versión vigente, sus
   contextos y la taxonomía que usan, en el formato del banco inicial o en la plantilla de hoja de
   cálculo, según elija; la plantilla incluye solo los ítems que puede representar e informa
   cuántos quedaron fuera.
2. **Given** un archivo exportado sin modificar,
   **When** se reimporta,
   **Then** no se crean ítems ni versiones.
3. **Given** un ítem con una versión publicada y otra en Borrador,
   **When** se exporta,
   **Then** el docente elige si exportar la versión publicada o la más reciente.

---

### User Story 7 - Cobertura del banco frente al examen (Priority: P3)

Como docente quiero ver la cobertura del banco frente a la distribución del examen (por ejemplo,
porcentaje de ítems por afirmación en Lectura crítica o por parte en Inglés) para saber dónde
faltan preguntas.

**Why this priority**: orienta el crecimiento del banco, pero no bloquea la práctica.

**Independent Test**: con el banco inicial publicado, abrir la cobertura de Inglés y verificar
que cada parte muestra cuántos ítems publicados tiene frente a lo que pide el examen.

**Acceptance Scenarios**:

1. **Given** un módulo,
   **When** el docente abre su cobertura,
   **Then** ve, por cada categoría de la taxonomía (afirmación, componente, parte, etc.), cuántos
   ítems publicados y En revisión hay, su porcentaje y el porcentaje objetivo según el examen.
2. **Given** categorías por debajo de su objetivo,
   **When** se muestra la cobertura,
   **Then** se resaltan las que más ítems necesitan, de forma perceptible sin depender solo del
   color.
3. **Given** la cobertura de un módulo,
   **When** el docente elige una categoría,
   **Then** ve la lista de sus ítems con su estado.

---

### User Story 8 - Estadísticas de cada ítem publicado (Priority: P3)

Como docente quiero ver las estadísticas de cada versión publicada (porcentaje de acierto,
opciones más elegidas y discriminación) para mejorarla o retirarla.

**Why this priority**: necesita respuestas de estudiantes, que llegan con la práctica (003); aquí
se define qué se mide y cómo se muestra.

**Independent Test**: con respuestas registradas para una versión, verificar el porcentaje de
acierto, la distribución por opción y el índice de discriminación; crear una versión nueva y
verificar que sus estadísticas empiezan en cero.

**Acceptance Scenarios**:

1. **Given** una versión publicada con suficientes respuestas,
   **When** el docente abre sus estadísticas,
   **Then** ve el número de respuestas, el porcentaje de acierto, el porcentaje que eligió cada
   opción y el índice de discriminación.
2. **Given** una versión con menos respuestas que el mínimo para que la cifra sea confiable,
   **When** se muestran sus estadísticas,
   **Then** se indica que aún no hay datos suficientes en lugar de mostrar valores engañosos.
3. **Given** una versión nueva de un ítem,
   **When** se publica,
   **Then** sus estadísticas empiezan en cero y las de la versión anterior siguen consultables.
4. **Given** ítems publicados con señales de problema (acierto muy alto o muy bajo,
   discriminación negativa o una opción incorrecta más elegida que la correcta),
   **When** el docente consulta el banco,
   **Then** puede filtrarlos para revisarlos.
5. **Given** las estadísticas de un ítem,
   **When** se muestran,
   **Then** son agregadas y no identifican a ningún estudiante.

---

### User Story 9 - Mantenimiento de la taxonomía (Priority: P3)

Como administrador quiero mantener la taxonomía de cada módulo y la distribución objetivo del
examen como datos, para ajustarlas cuando el ICFES publique una guía nueva sin cambiar la
aplicación.

**Why this priority**: el banco inicial trae la taxonomía vigente; los cambios son esporádicos.

**Independent Test**: agregar una evidencia nueva a una afirmación, usarla en un ítem e intentar
borrar una evidencia en uso; verificar que solo puede desactivarse.

**Acceptance Scenarios**:

1. **Given** un administrador,
   **When** agrega o edita una categoría de la taxonomía o el porcentaje objetivo de una
   categoría,
   **Then** el cambio queda disponible para los formularios, la importación y la cobertura.
2. **Given** una categoría usada por algún ítem,
   **When** el administrador intenta borrarla,
   **Then** el sistema lo impide y ofrece desactivarla; una categoría desactivada no se ofrece en
   ítems nuevos y los ítems que la usan siguen válidos.
3. **Given** un docente sin rol Administrador,
   **When** intenta cambiar la taxonomía,
   **Then** se le niega el acceso.

---

### Edge Cases

- Dos docentes editan la misma versión en Borrador al mismo tiempo: el segundo en guardar recibe
  un aviso de conflicto con los cambios del otro y no se pierde ninguno sin que lo decida.
- Un archivo de importación supera el tamaño o el número máximo de ítems por lote: se rechaza
  antes de procesarlo, indicando el límite.
- Un archivo no tiene el formato esperado (columnas faltantes, esquema distinto, codificación
  ilegible): se rechaza completo con un mensaje que indica qué no se reconoce.
- Un ítem del archivo referencia un contexto que no está ni en el archivo ni en el banco: error
  de ese ítem.
- Un ítem de Inglés parte 1 indica una clave que no está entre las opciones compartidas de su
  contexto: error de ese ítem.
- Un contexto de opciones compartidas cambia mientras sus ítems están publicados: los cambios
  generan versiones nuevas de los ítems afectados, que pasan por revisión.
- Se retira un ítem que es el único publicado de una categoría: se permite, y la cobertura lo
  refleja.
- Un docente pierde el rol Docente con ítems en Borrador: sus ítems siguen en el banco y otro
  docente puede continuarlos.
- Una versión la creó una persona y la modificó otra: ninguna de las dos puede aprobarla; solo un
  tercer administrador.
- El único administrador activo creó o modificó un ítem: no puede aprobarlo y el ítem queda En
  revisión hasta que haya otro administrador; la pantalla de revisión lo indica.
- Una importación se interrumpe a mitad de la confirmación: o entran todos los ítems válidos o no
  entra ninguno; no quedan importaciones a medias.
- Un ítem retirado tiene respuestas históricas: las respuestas y las estadísticas de sus versiones
  se conservan.
- Un texto de Lectura crítica tiene exactamente 500 palabras: se acepta.

## Requirements *(mandatory)*

### Functional Requirements

**Estructura del contenido**

- **FR-001**: El sistema DEBE manejar los módulos y su taxonomía (competencias, afirmaciones,
  evidencias, componentes, tipos de situación, tipos de texto, partes de Inglés, rúbricas y
  condición de pertinencia) como datos configurables, no como valores fijos.
- **FR-002**: Cada ítem de Lectura crítica, Razonamiento cuantitativo y Competencias ciudadanas
  DEBE ser de selección múltiple con única respuesta, tener 4 opciones y estar etiquetado con
  competencia, afirmación y evidencia; los de Razonamiento cuantitativo además con componente y
  tipo de situación, y los contextos de Lectura crítica con tipo de texto.
- **FR-003**: Los ítems de Inglés DEBEN pertenecer a una de las siete partes y cumplir su formato:
  la parte 1 es de emparejamiento contra una lista de 8 opciones compartidas por su contexto
  (5 descripciones por contexto); las partes 2 a 5 tienen 3 opciones; las partes 6 y 7 tienen 4.
- **FR-004**: Las consignas de Comunicación escrita DEBEN estar asociadas a una rúbrica y a una
  condición de pertinencia, y no tienen opciones.
- **FR-005**: Varios ítems DEBEN poder compartir un contexto de tipo texto, tabla, imagen o lista
  de opciones compartidas.
- **FR-006**: Cada opción DEBE tener retroalimentación: la correcta explica por qué lo es y cada
  incorrecta el error que representa. Cada ítem DEBE tener una explicación general.
- **FR-007**: Los textos de los contextos de Lectura crítica NO DEBEN superar 500 palabras.
- **FR-008**: Cada ítem DEBE tener un identificador estable entre versiones, una dificultad
  (baja, media o alta), un origen (por ejemplo, banco inicial, docente o IA) y un autor.
- **FR-009**: Toda imagen DEBE tener texto alternativo, y el contenido DEBE poder presentarse
  cumpliendo WCAG 2.2 AA en la vista del estudiante.

**Estados, revisión y versiones**

- **FR-010**: Cada versión de un ítem DEBE estar en uno de estos estados: Borrador, En revisión,
  Publicado o Retirado, con las transiciones Borrador → En revisión (enviar), En revisión →
  Publicado (aprobar), En revisión → Borrador (devolver con comentarios), En revisión → Retirado
  (rechazar con motivo) y Publicado → Retirado (retirar con motivo).
- **FR-011**: Solo las versiones Publicadas DEBEN llegar a los estudiantes; un ítem tiene a lo
  sumo una versión Publicada a la vez.
- **FR-012**: Ninguna persona que haya creado o modificado una versión DEBE poder aprobarla.
- **FR-013**: Solo los administradores DEBEN poder aprobar, devolver con comentarios, rechazar y
  retirar; los docentes DEBEN poder enviar a revisión y comentar.
- **FR-014**: Antes de aprobar un ítem, el administrador DEBE confirmar que verificó su alineación con la
  guía del ICFES y que no reproduce preguntas del ICFES; la confirmación queda registrada.
- **FR-015**: Editar o reimportar con cambios un ítem Publicado o Retirado DEBE crear una versión
  nueva; la versión Publicada sigue entregándose hasta que la nueva se apruebe, y al aprobarse la
  nueva, la anterior pasa a Retirado.
- **FR-016**: Editar o reimportar un ítem en Borrador o En revisión DEBE actualizar su versión en
  curso sin crear otra; si estaba En revisión, DEBE volver a Borrador o a una nueva revisión.
- **FR-017**: Las respuestas de los estudiantes DEBEN conservar la versión respondida, y las
  estadísticas DEBEN calcularse por versión.
- **FR-018**: Cada ítem DEBE tener un historial con cada versión, su estado, autor, revisor,
  comentarios, motivos, fechas y diferencias frente a la versión anterior.
- **FR-019**: Los ítems del banco inicial y los generados con IA DEBEN entrar En revisión y con su
  origen visible para el revisor.
- **FR-020**: Cambiar un contexto usado por ítems Publicados DEBE generar versiones nuevas de esos
  ítems, que pasan por revisión.

**Carga inicial**

- **FR-021**: En cada despliegue, el sistema DEBE aplicar el banco inicial incluido en el
  proyecto (taxonomía, rúbrica, contextos, ítems y consignas): lo carga completo si el banco está
  vacío y, si ya existe, agrega los elementos con identificador nuevo, En revisión.
- **FR-022**: Un ítem del banco inicial ya cargado DEBE recibir una versión nueva En revisión
  solo si su contenido en el archivo cambió desde la última carga; si no cambió, NO DEBE tocarse
  aunque los docentes lo hayan modificado. Repetir la carga con el mismo archivo NO DEBE crear
  elementos ni versiones.
- **FR-022a**: Si un ítem cambió en el archivo y tiene una versión en Borrador o En revisión
  hecha por un docente, el cambio NO DEBE aplicarse a ese ítem; el resultado de la carga DEBE
  listarlo para incorporarlo a mano.
- **FR-023**: Si el archivo del banco inicial tiene errores, la carga NO DEBE aplicar ningún
  cambio y DEBE informar cada error.

**Creación, edición y vista previa**

- **FR-024**: Los docentes DEBEN poder crear y editar ítems, consignas y contextos, incluidos los
  que creó otra persona, con validación de las reglas del módulo o de la parte junto a cada campo;
  cada cambio DEBE quedar registrado con quién lo hizo.
- **FR-025**: Los docentes DEBEN poder previsualizar un ítem o consigna con su contexto tal como lo
  verá el estudiante en el celular, incluida la retroalimentación de cada opción.
- **FR-026**: Al editar un contexto compartido, el sistema DEBE mostrar cuántos ítems lo usan y
  cuántos están Publicados.
- **FR-027**: Si dos personas modifican la misma versión a la vez, el sistema DEBE detectar el
  conflicto y no descartar cambios sin aviso.

**Importación y exportación**

- **FR-028**: Los docentes DEBEN poder importar en lote desde un archivo con el formato del banco
  inicial y desde una plantilla de hoja de cálculo que la aplicación ofrece para descargar.
- **FR-029**: La plantilla de hoja de cálculo DEBE cubrir solo ítems de selección con su contexto
  de texto, una fila por ítem. Los ítems de Inglés parte 1, los contextos con imagen o tabla y las
  consignas de escritura DEBEN importarse con el formato del banco inicial; si llegan en la
  plantilla, se marcan con error indicándolo.
- **FR-030**: Toda importación DEBE validarse completa y mostrar una vista previa (nuevos,
  actualizaciones con sus diferencias, sin cambios y con errores) antes de guardar nada.
- **FR-031**: La validación DEBE comprobar, por ítem: exactamente una opción correcta; número de
  opciones acorde al módulo o a la parte; retroalimentación en todas las opciones; explicación
  general; códigos de taxonomía existentes y activos; contextos referenciados existentes; textos
  de Lectura crítica de máximo 500 palabras; texto alternativo de las imágenes, y duplicados.
- **FR-032**: Un ítem cuyo contenido normalizado (enunciado, opciones y contexto) coincida con el
  de otro ítem del banco o del mismo archivo con distinto identificador DEBE marcarse como
  duplicado y no importarse.
- **FR-033**: El reporte de errores DEBE indicar, por ítem, su identificador, el campo y la regla
  incumplida, y DEBE poder descargarse.
- **FR-034**: Al confirmar, DEBEN entrar todos los ítems válidos o ninguno (sin importaciones a
  medias); los inválidos quedan fuera con su motivo, y el docente elige si los nuevos entran en
  Borrador o En revisión.
- **FR-035**: Importar un ítem con un identificador existente DEBE seguir las reglas de versiones
  (FR-015 y FR-016); si el contenido no cambió, NO DEBE crear ninguna versión.
- **FR-036**: Al confirmar una importación, el docente DEBE declarar que los ítems son originales y
  no reproducen preguntas del ICFES; la declaración, el archivo de origen, quién importó y cuándo
  DEBEN quedar registrados.
- **FR-037**: El sistema DEBE limitar el tamaño del archivo y el número de ítems por lote, y
  rechazar antes de procesar los que lo superen.
- **FR-038**: Los docentes DEBEN poder exportar el banco completo o filtrado por módulo, estado,
  origen, categoría de la taxonomía y dificultad, en el formato del banco inicial o en la
  plantilla de hoja de cálculo (solo con los ítems que esta puede representar, informando cuántos
  quedaron fuera); un archivo exportado y reimportado sin cambios NO DEBE crear
  ítems ni versiones.

**Cobertura y estadísticas**

- **FR-039**: El sistema DEBE mostrar, por módulo y por categoría de la taxonomía, cuántos ítems
  hay Publicados y En revisión, su porcentaje y el porcentaje objetivo según la distribución del
  examen, y resaltar las categorías por debajo del objetivo sin depender solo del color.
- **FR-040**: La distribución objetivo del examen DEBE ser un dato configurable por el
  administrador; los valores iniciales vienen del banco inicial y de la guía vigente del ICFES.
- **FR-041**: Para cada versión Publicada de un ítem de selección, el sistema DEBE mostrar el
  número de respuestas, el porcentaje de acierto, el porcentaje de elección de cada opción y un
  índice de discriminación, calculados con la primera respuesta de cada estudiante a esa versión.
- **FR-042**: Mientras una versión tenga menos de 30 primeras respuestas, el sistema DEBE indicar
  que no hay datos suficientes en lugar de mostrar las cifras como confiables.
- **FR-043**: Los docentes DEBEN poder filtrar los ítems con señales de problema: acierto mayor al
  90 % o menor al 20 %, discriminación negativa, o una opción incorrecta más elegida que la
  correcta.
- **FR-044**: Las estadísticas DEBEN ser agregadas y NO DEBEN identificar a ningún estudiante.

**Taxonomía y permisos**

- **FR-045**: Solo los administradores DEBEN poder cambiar la taxonomía, las rúbricas y la
  distribución objetivo; una categoría en uso NO DEBE poder borrarse, solo desactivarse.
- **FR-046**: Solo los docentes y administradores DEBEN poder ver el banco fuera de la práctica;
  estudiantes e invitados NO DEBEN poder consultar ítems no publicados, claves ni estadísticas.
- **FR-047**: Toda transición de estado, importación, exportación y cambio de taxonomía DEBE
  registrarse en la auditoría (quién, qué y cuándo), sin datos personales en los logs.

### Key Entities *(include if feature involves data)*

- **Módulo**: uno de los cinco módulos genéricos, con su tipo de pregunta, número de opciones por
  ítem (fijo o por parte), restricciones (por ejemplo, máximo de palabras) y número de preguntas
  en el examen.
- **Categoría de la taxonomía**: competencia, afirmación, evidencia, componente, tipo de situación,
  tipo de texto o parte de Inglés; tiene código, nombre, jerarquía (una evidencia pertenece a una
  afirmación, que pertenece a una competencia), estado activo o inactivo y porcentaje objetivo.
- **Rúbrica**: dimensiones de calificación de la escritura (planteamiento, organización y forma de
  expresión) con sus niveles, y la condición de pertinencia.
- **Contexto**: material compartido (texto, tabla, imagen con texto alternativo o lista de
  opciones compartidas) con módulo, tipo de texto o parte, origen y versiones.
- **Ítem**: identificador estable, módulo, taxonomía, dificultad, origen y versiones.
- **Versión de ítem**: contenido (enunciado, opciones con retroalimentación y marca de correcta, o
  clave contra las opciones del contexto, explicación general), estado, autor, personas que la
  modificaron, revisor, comentarios, motivos y fechas.
- **Consigna**: tarea abierta de escritura con su pregunta, contexto, rúbrica y versiones.
- **Importación**: archivo de origen, quién y cuándo, resultado por ítem (nuevo, actualizado, sin
  cambios, con error y su motivo) y declaración de originalidad.
- **Estadística de versión**: agregados por versión publicada: respuestas, acierto, elección por
  opción e índice de discriminación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El banco inicial (43 ítems, 3 consignas y 8 contextos) se carga sin errores en un
  despliegue desde cero.
- **SC-002**: Repetir la carga inicial o reimportar el mismo archivo crea 0 ítems y 0 versiones
  nuevos, y una carga con un archivo actualizado no modifica ningún ítem que no haya cambiado en
  el archivo.
- **SC-003**: Importar o actualizar 500 ítems válidos, desde que el docente confirma hasta que el
  resultado está disponible, tarda menos de 1 minuto.
- **SC-004**: La vista previa y el reporte de errores de un archivo de 500 ítems están listos en
  menos de 30 segundos.
- **SC-005**: El 100 % de los ítems que llegan a los estudiantes fue aprobado por una persona
  distinta de quien lo creó o modificó.
- **SC-006**: El 100 % de las respuestas históricas conserva la versión respondida después de que
  el ítem cambia o se retira.
- **SC-007**: Un docente puede crear un ítem completo con su contexto, previsualizarlo y enviarlo
  a revisión en menos de 10 minutos la primera vez, sin ayuda.
- **SC-008**: Un archivo exportado y reimportado sin cambios produce una vista previa con 0
  cambios.
- **SC-009**: Con 10 000 ítems en el banco, buscar y filtrar ítems, abrir la cobertura de un módulo
  y abrir las estadísticas de un ítem muestran el resultado en menos de 2 segundos.
- **SC-010**: Exportar el banco completo de 10 000 ítems tarda menos de 1 minuto.

## Assumptions

- Los roles Docente y Administrador, la auditoría y la autenticación vienen de 001; esta
  funcionalidad no crea roles nuevos: la revisión es del rol Administrador (FR-013).
- El registro de quién modificó cada versión (FR-024) es lo que impide la autoaprobación
  (FR-012).
- Debe haber al menos dos administradores para revisar ítems que un administrador creó o
  modificó; con uno solo, esos ítems esperan a que haya otro.
- Rechazar un ítem en revisión lo lleva a Retirado con su motivo; no se crea un estado
  "Rechazado" aparte, para respetar los cuatro estados de la descripción.
- Al aprobar una versión nueva, la versión publicada anterior pasa a Retirado automáticamente.
- Las respuestas de los estudiantes llegan con la práctica (003); hasta entonces las estadísticas
  muestran "sin datos suficientes".
- El índice de discriminación usa un método estándar de la psicometría clásica; el plan elige
  cuál. El mínimo de 30 respuestas sigue la práctica habitual para cifras estables.
- Las estadísticas usan la primera respuesta de cada estudiante a cada versión, para que la
  repetición espaciada no infle el acierto.
- No es posible detectar de forma automática si un ítem copia una pregunta del ICFES; el control
  es la declaración de originalidad al importar (FR-036) y la confirmación del revisor (FR-014).
- La detección de duplicados compara el contenido normalizado (mayúsculas, espacios y
  puntuación); la detección de paráfrasis queda fuera.
- Las imágenes de los contextos se suben en el editor; los archivos de importación las referencian
  por el identificador de una imagen ya cargada en el banco.
- Los límites por lote (FR-037) se fijan en el plan; deben permitir al menos 500 ítems por archivo.
- El banco se dimensiona para hasta 10 000 ítems (SC-009); más allá de eso se revisará la meta.
- La calificación de los textos de Comunicación escrita (010) y la generación de ítems con IA
  (011) son otras funcionalidades; aquí solo se guardan sus consignas, rúbricas y el origen "ia".

## Out of Scope

- La práctica de los estudiantes, la entrega de ítems y el registro de respuestas (003).
- El motor adaptativo y la selección de ítems por dominio (005), y los simulacros (006).
- La calificación de los textos argumentativos (010).
- La generación de ítems con IA (011).
- La detección automática de plagio o de paráfrasis de preguntas del ICFES.
- La traducción del banco a otros idiomas distintos del español (salvo el contenido de Inglés).
