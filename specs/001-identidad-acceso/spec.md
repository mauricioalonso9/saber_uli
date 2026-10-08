# Feature Specification: Identidad, acceso institucional e invitados

**Feature Branch**: `001-identidad-acceso`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Usa la especificación 001 de la sección 4 de @docs/SABER_ULI_KIT_SDD.md"
(identidad, acceso, roles, perfil y consentimiento de datos en Saber Uli).

## Contexto

Saber Uli es un juego tipo Duolingo para preparar los cinco módulos genéricos de las pruebas
Saber Pro del ICFES, dirigido a la comunidad de la Universidad Libre, con acceso limitado para
invitados. Esta funcionalidad define quién puede entrar, con qué identidad, con qué permisos y
bajo qué autorización de tratamiento de datos personales.

**Actores**

- **Estudiante Unilibre**: miembro de la comunidad institucional que se prepara para Saber Pro.
- **Invitado**: persona externa a Unilibre con acceso temporal por invitación.
- **Docente**: crea y revisa contenido y ve el progreso de sus grupos.
- **Director de programa**: ve la analítica de su programa académico.
- **Administrador**: gestiona usuarios, invitaciones, programas, grupos y parámetros.

## Clarifications

### Session 2026-10-05

- Q: Si un usuario ya ingresó y el celular se queda sin conexión, ¿cuánto tiempo puede seguir
  usando la app sin volver a autenticarse? → A: 7 días sin conexión; al reconectar se validan
  vencimiento, revocación y autorización antes de sincronizar.
- Q: ¿Qué datos personales de los estudiantes pueden ver los docentes de sus grupos y los
  directores de programa? → A: Docentes ven nombre y progreso de los estudiantes de sus grupos;
  directores ven solo datos agregados o seudonimizados de su programa.
- Q: Cuando vence o se revoca el acceso de un invitado, ¿qué pasa con su cuenta y sus datos
  personales? → A: Se conservan 90 días por si se renueva el acceso; después se suprimen de forma
  automática, con la misma regla de la supresión voluntaria.
- Q: Cuando un usuario institucional deja de estar en el directorio de Unilibre (se gradúa o se
  retira), ¿qué pasa con su cuenta y sus datos personales? → A: La cuenta queda inactiva; si la
  persona no vuelve a ingresar en 1 año, sus datos personales se suprimen de forma automática
  (misma regla que la supresión voluntaria). Como Saber Uli no consulta el directorio fuera del
  ingreso (FR-004), el plazo se cuenta desde el último ingreso exitoso.
- Q: Antes de suprimir automáticamente los datos de una cuenta, ¿se le avisa a la persona? →
  A: Sí, con un correo 30 días antes que explica cómo evitar la supresión (volver a ingresar o
  pedir renovación).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingreso con la cuenta institucional (Priority: P1)

Como miembro de la comunidad Unilibre quiero ingresar con mi cuenta institucional de
Microsoft 365, sin crear otra contraseña. En mi primer ingreso mi cuenta se crea
automáticamente con mi nombre y correo institucional y el rol Estudiante.

**Why this priority**: es la puerta de entrada de la población principal; sin ella ninguna otra
funcionalidad del producto es utilizable.

**Independent Test**: ingresar con una cuenta de prueba del inquilino Unilibre y con una cuenta
Microsoft externa; verificar que la primera entra con cuenta creada y la segunda es rechazada.

**Acceptance Scenarios**:

1. **Given** una persona con cuenta Microsoft 365 de Unilibre que nunca ha ingresado,
   **When** elige "Ingresar con mi cuenta Unilibre" y se autentica,
   **Then** se crea su cuenta con nombre y correo institucional, rol Estudiante, y pasa al paso
   de autorización de datos.
2. **Given** una persona con una cuenta Microsoft que no pertenece al inquilino de Unilibre,
   **When** intenta ingresar,
   **Then** el acceso es rechazado con un mensaje claro que explica que solo se admiten cuentas
   institucionales y cómo obtener una invitación, y no se crea ninguna cuenta.
3. **Given** un usuario institucional que ya ingresó antes,
   **When** vuelve a autenticarse,
   **Then** entra a su cuenta existente sin duplicarla, y su nombre se actualiza si cambió en el
   directorio institucional.
4. **Given** un usuario con sesión abierta,
   **When** cierra sesión,
   **Then** la sesión termina en ese dispositivo y se requiere autenticarse de nuevo.

---

### User Story 2 - Autorización de tratamiento de datos (Priority: P1)

Como cualquier usuario quiero aceptar o rechazar de forma explícita la política de tratamiento
de datos antes de usar la plataforma, y luego poder consultar mi autorización o revocarla.

**Why this priority**: es un requisito legal (Ley 1581 de 2012); sin autorización vigente no se
puede usar la plataforma, así que bloquea a todos los demás flujos.

**Independent Test**: ingresar con un usuario nuevo, rechazar la política (sin acceso), luego
aceptarla (acceso concedido), consultarla y revocarla (acceso suspendido).

**Acceptance Scenarios**:

1. **Given** un usuario autenticado sin autorización vigente,
   **When** se le presenta la política,
   **Then** ve la finalidad del tratamiento, los datos que se recogen, sus derechos y los
   canales para ejercerlos, con las opciones "Acepto" y "No acepto" (ninguna preseleccionada).
2. **Given** el usuario elige "Acepto",
   **When** confirma,
   **Then** se registra la autorización con fecha y hora, versión de la política y medio de
   aceptación, y el usuario continúa.
3. **Given** el usuario elige "No acepto",
   **When** confirma,
   **Then** no puede usar ninguna función de la plataforma, se le explica por qué y puede
   aceptar más adelante o solicitar la eliminación de su cuenta.
4. **Given** un usuario con autorización vigente,
   **When** consulta su autorización,
   **Then** ve qué versión aceptó, cuándo, y el texto de esa versión.
5. **Given** un usuario con autorización vigente,
   **When** la revoca,
   **Then** se registra la revocación con fecha, su acceso queda suspendido y se le ofrece
   aceptar de nuevo o solicitar la supresión de sus datos.
6. **Given** se publica una nueva versión de la política,
   **When** un usuario con autorización de una versión anterior ingresa,
   **Then** debe aceptar la nueva versión antes de continuar.

---

### User Story 3 - Completar el perfil en el primer ingreso (Priority: P1)

En mi primer ingreso quiero completar solo programa académico, semestre, fecha estimada de
presentación de Saber Pro y meta diaria; el resto se toma de mi cuenta institucional.

**Why this priority**: el programa y la fecha de presentación permiten personalizar la ruta y
agrupar la analítica; es el último paso antes de la primera lección.

**Independent Test**: tras autorizar los datos, completar el perfil y llegar a la pantalla de la
primera lección en menos de 1 minuto desde el inicio del ingreso.

**Acceptance Scenarios**:

1. **Given** un estudiante institucional con autorización vigente y perfil incompleto,
   **When** llega al paso de perfil,
   **Then** ve su nombre y correo ya cargados (no editables) y solo debe elegir programa
   académico de una lista, semestre, fecha estimada de presentación y meta diaria.
2. **Given** el estudiante completa los cuatro campos,
   **When** guarda,
   **Then** queda en la pantalla de inicio lista para empezar su primera lección.
3. **Given** un estudiante con perfil completo,
   **When** edita su programa, semestre, fecha de presentación o meta diaria,
   **Then** los cambios se guardan y se aplican desde ese momento.
4. **Given** un invitado en su primer ingreso,
   **When** llega al paso de perfil,
   **Then** solo indica su nombre, fecha estimada de presentación (opcional) y meta diaria; no se
   le pide programa ni semestre.

---

### User Story 4 - Acceso de invitados (Priority: P2)

Como invitado quiero acceder con una invitación enviada a mi correo, sin necesitar una cuenta
Unilibre ni crear una contraseña.

**Why this priority**: amplía el alcance a personas externas (por ejemplo, convenios o aspirantes
de otras sedes), pero no es necesario para que la comunidad institucional use el producto.

**Independent Test**: enviar una invitación a un correo de prueba, ingresar con el enlace
recibido, verificar las restricciones del invitado y verificar que tras el vencimiento no entra.

**Acceptance Scenarios**:

1. **Given** un invitado con una invitación vigente,
   **When** abre el enlace de acceso que recibió en su correo,
   **Then** ingresa sin contraseña, se crea su cuenta con rol Invitado y pasa al paso de
   autorización de datos.
2. **Given** un invitado ya registrado con acceso vigente,
   **When** solicita ingresar con su correo,
   **Then** recibe un nuevo enlace de acceso de un solo uso y de corta duración.
3. **Given** un enlace de acceso ya usado o vencido,
   **When** alguien lo abre,
   **Then** no se concede acceso y se le indica que solicite un enlace nuevo.
4. **Given** un invitado cuya fecha de vencimiento de acceso ya pasó,
   **When** intenta ingresar o usar una sesión abierta,
   **Then** se le niega el acceso con un mensaje que indica que su acceso venció y a quién
   contactar.
5. **Given** un invitado con acceso vigente,
   **When** practica, hace simulacros y gana XP,
   **Then** puede hacerlo, pero no aparece en ligas institucionales ni en la analítica de
   programa.

---

### User Story 5 - Gestión de invitaciones (Priority: P2)

Como administrador o docente quiero enviar invitaciones individuales o por lote, con fecha de
vencimiento del acceso, y revocarlas. Un docente gestiona solo las invitaciones que él envió; un
administrador gestiona todas.

**Why this priority**: es la contraparte necesaria de la historia 4.

**Independent Test**: enviar una invitación individual y un lote con correos válidos, inválidos y
duplicados; revisar el reporte del lote; revocar una invitación y comprobar que el invitado
pierde el acceso.

**Acceptance Scenarios**:

1. **Given** un usuario autorizado para invitar,
   **When** envía una invitación con correo, nombre opcional y fecha de vencimiento del acceso,
   **Then** se envía el correo de invitación y la invitación queda en estado "Enviada".
2. **Given** un usuario autorizado para invitar,
   **When** carga un lote de invitaciones,
   **Then** el sistema valida cada fila, muestra un reporte por fila (válida, correo inválido,
   duplicada, ya invitada, correo institucional) y solo envía las válidas tras su confirmación.
3. **Given** una invitación dirigida a un correo del dominio institucional de Unilibre,
   **When** se intenta crear,
   **Then** se rechaza indicando que esa persona debe ingresar con su cuenta institucional.
4. **Given** una invitación pendiente o un invitado activo,
   **When** el administrador la revoca,
   **Then** el enlace deja de funcionar, toda sesión abierta del invitado termina y el cambio
   queda auditado.
5. **Given** un invitado activo, o uno cuyo acceso venció o fue revocado hace menos de 90 días,
   **When** quien lo invitó o un administrador amplía o reduce su fecha de vencimiento,
   **Then** el nuevo vencimiento se aplica de inmediato, el invitado conserva su progreso y el
   cambio queda auditado.
6. **Given** el listado de invitaciones,
   **When** el administrador lo consulta,
   **Then** puede filtrarlo por estado (Enviada, Aceptada, Vencida, Revocada) y ver quién invitó
   y cuándo.
7. **Given** un docente,
   **When** consulta el listado de invitaciones,
   **Then** ve solo las que él envió y puede reenviarlas, modificar su vencimiento o revocarlas,
   pero no las de otros docentes ni las de administradores.
8. **Given** un docente que envía una invitación,
   **When** indica un vencimiento posterior al plazo máximo para docentes,
   **Then** la invitación se rechaza indicando el plazo máximo permitido.

---

### User Story 6 - Roles y grupos (Priority: P2)

Como administrador quiero asignar roles a los usuarios y asociar docentes a grupos o cohortes de
estudiantes.

**Why this priority**: habilita a docentes y directores, que son necesarios para el banco de
ítems (002) y el panel docente (008), pero no para que un estudiante practique.

**Independent Test**: asignar a un usuario los roles Docente y Director de programa, asociarlo a
un grupo y verificar que obtiene los permisos de ambos roles; retirar un rol y verificar que los
pierde.

**Acceptance Scenarios**:

1. **Given** un usuario institucional con rol Estudiante,
   **When** el administrador le asigna el rol Docente,
   **Then** conserva el rol Estudiante y obtiene además los permisos de Docente.
2. **Given** un usuario con rol Director de programa,
   **When** el administrador le asigna uno o varios programas,
   **Then** solo puede ver información agregada o seudonimizada de esos programas, sin nombres
   ni correos de estudiantes.
3. **Given** un administrador,
   **When** crea un grupo o cohorte, le agrega estudiantes y le asocia uno o varios docentes,
   **Then** esos docentes pueden ver el nombre y el progreso de los estudiantes del grupo, sin su
   correo, y de ningún otro grupo.
4. **Given** un administrador,
   **When** intenta retirar el rol Administrador del último administrador activo,
   **Then** la acción se rechaza.
5. **Given** un invitado,
   **When** un administrador intenta asignarle un rol distinto de Invitado o agregarlo a un
   grupo institucional,
   **Then** la acción se rechaza.
6. **Given** un administrador,
   **When** desactiva o reactiva una cuenta,
   **Then** el usuario desactivado no puede ingresar y sus sesiones terminan.

---

### User Story 7 - Supresión de la cuenta y de los datos personales (Priority: P3)

Como usuario quiero solicitar la eliminación de mi cuenta y de mis datos personales.

**Why this priority**: es un derecho legal que debe existir desde el lanzamiento, pero su uso es
poco frecuente.

**Independent Test**: un usuario solicita la supresión, confirma, y se verifica que ya no puede
ingresar, que sus datos personales no aparecen en ninguna vista y que la acción quedó auditada.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado (con o sin autorización vigente),
   **When** solicita eliminar su cuenta,
   **Then** se le explica qué se elimina, qué se conserva de forma anónima y que la acción es
   irreversible, y debe confirmarlo explícitamente.
2. **Given** el usuario confirma la solicitud,
   **When** se procesa,
   **Then** su acceso termina de inmediato y, dentro del plazo definido, sus datos personales se
   eliminan; los registros que deban conservarse (estadísticas de ítems, auditoría) quedan sin
   datos que lo identifiquen.
3. **Given** un usuario que eliminó su cuenta,
   **When** vuelve a ingresar con la misma cuenta institucional,
   **Then** se le trata como un usuario nuevo, sin historial previo.
4. **Given** un administrador,
   **When** consulta las solicitudes de supresión,
   **Then** ve su estado (Recibida, En proceso, Completada) y la fecha límite de cada una.
5. **Given** el último administrador activo,
   **When** solicita la supresión de su cuenta,
   **Then** la solicitud se rechaza indicando que primero debe asignarse el rol Administrador a
   otra persona.

---

### User Story 8 - Consulta y rectificación de mis datos (Priority: P3)

Como usuario quiero consultar todos los datos personales que la plataforma tiene sobre mí y
corregir los que sean editables.

**Why this priority**: derecho legal de consulta y rectificación; complementa la historia 7.

**Independent Test**: un usuario abre "Mis datos", ve el listado completo de sus datos
personales, descarga una copia y corrige un dato editable.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado,
   **When** abre "Mis datos",
   **Then** ve sus datos de identidad, de perfil, sus roles, su historial de autorizaciones y
   puede descargar una copia en un formato legible.
2. **Given** un usuario institucional que detecta un error en su nombre o correo,
   **When** consulta cómo corregirlo,
   **Then** se le indica que esos datos provienen del directorio institucional y el canal para
   corregirlos allí.

### Edge Cases

- Un usuario institucional es retirado del directorio de Unilibre (por ejemplo, egresa o se
  retira): ya no puede autenticarse; al cumplirse 1 año desde su último ingreso exitoso, sus
  datos personales se suprimen automáticamente (FR-034b).
- Un estudiante institucional activo pasa 1 año sin ingresar: se aplica la misma supresión;
  si vuelve después, entra como usuario nuevo, sin historial previo.
- Una persona recibe una invitación como invitado y luego ingresa con su cuenta institucional:
  son cuentas distintas; la invitación a correos institucionales se rechaza desde el origen.
- El mismo correo aparece dos veces en un lote de invitaciones, o ya tiene una invitación
  vigente: se marca como duplicado y no se envía de nuevo; reenviar es una acción explícita.
- El correo de invitación no llega o rebota: el administrador ve el estado y puede reenviarla.
- Se usa un enlace de acceso desde otro dispositivo o navegador: funciona una sola vez,
  independientemente del dispositivo.
- Se revoca a un invitado o vence su acceso mientras tiene una sesión abierta: con conexión,
  pierde el acceso en su siguiente acción; sin conexión, lo pierde al reconectar o, a más
  tardar, 7 días después de su última validación, y su actividad pendiente no se sincroniza.
- Se invita de nuevo a un invitado cuyos datos ya se suprimieron (más de 90 días después del
  vencimiento): se le trata como un invitado nuevo, sin historial previo.
- Un usuario pasa más de 7 días sin conexión: la app le pide reconectarse y autenticarse antes
  de seguir; su actividad pendiente se conserva en el celular hasta entonces.
- Se publica una nueva versión de la política mientras un usuario tiene una sesión abierta: se
  le pide aceptarla en su siguiente navegación antes de continuar.
- El servicio de identidad institucional no está disponible: se muestra un mensaje de
  indisponibilidad temporal; los invitados no se ven afectados.
- Un usuario intenta acceder a funciones de un rol que no tiene (por ejemplo, abrir la gestión
  de invitaciones como Estudiante): se le niega el acceso sin revelar información de la función.
- El usuario cierra la aplicación a mitad del primer ingreso (antes de autorizar o de completar
  el perfil): al volver, retoma en el paso pendiente.
- El primer ingreso y la autorización de datos requieren conexión; sin conexión se informa que
  se necesita red para este paso.
- El último administrador activo pasa 1 año sin ingresar o solicita la supresión de su cuenta:
  no se suprime; la solicitud voluntaria se rechaza explicando que primero debe existir otro
  administrador (FR-034d).
- Una invitación nunca aceptada vence o se revoca: 90 días después se borran el correo y el
  nombre del invitado; la invitación queda solo como registro sin datos personales (FR-034e).
- Un docente con contenido creado solicita la supresión: el contenido permanece, pero su
  autoría pasa a mostrarse sin datos personales.

## Requirements *(mandatory)*

### Functional Requirements

**Ingreso institucional**

- **FR-001**: El sistema DEBE permitir ingresar con la cuenta Microsoft 365 institucional, sin
  que el usuario cree ni almacene una contraseña en Saber Uli.
- **FR-002**: El sistema DEBE admitir como comunidad institucional solo cuentas del inquilino
  Microsoft 365 de Unilibre y rechazar cualquier otra cuenta Microsoft con un mensaje claro que
  indique la razón y la alternativa (solicitar invitación).
- **FR-003**: En el primer ingreso institucional el sistema DEBE crear la cuenta con nombre y
  correo institucional tomados del directorio, y asignar el rol Estudiante.
- **FR-004**: El sistema DEBE tomar del directorio institucional solo nombre, correo y un
  identificador estable de la persona; NO DEBE solicitar ni almacenar otros datos del
  directorio.
- **FR-005**: El sistema DEBE reconocer al mismo usuario institucional en ingresos posteriores
  sin duplicar su cuenta, aunque cambie su nombre o correo en el directorio.

**Invitados**

- **FR-006**: El sistema DEBE permitir a administradores y docentes enviar invitaciones
  individuales y por lote, cada una con fecha de vencimiento del acceso. Un docente solo DEBE
  ver, reenviar, modificar y revocar las invitaciones que él mismo envió; un administrador DEBE
  poder gestionar todas.
- **FR-006a**: La fecha de vencimiento del acceso de una invitación enviada por un docente NO
  DEBE superar el plazo máximo configurado por un administrador; los administradores no tienen
  ese límite.
- **FR-007**: El acceso de invitados DEBE hacerse mediante enlaces enviados al correo, de un solo
  uso y de corta duración, sin contraseñas.
- **FR-008**: El sistema DEBE rechazar invitaciones dirigidas a correos del dominio institucional
  de Unilibre.
- **FR-009**: El sistema DEBE validar los lotes de invitaciones fila por fila, mostrar el
  resultado de cada fila y enviar solo las válidas tras confirmación.
- **FR-010**: El sistema DEBE permitir revocar invitaciones y el acceso de invitados, y modificar
  su fecha de vencimiento; el efecto DEBE aplicarse a las sesiones abiertas.
- **FR-011**: El sistema DEBE impedir todo ingreso de un invitado cuyo acceso venció o fue
  revocado.
- **FR-012**: Los invitados DEBEN poder practicar, hacer simulacros y ganar XP, y NO DEBEN
  aparecer en ligas institucionales ni en la analítica de programa.
- **FR-013**: El sistema DEBE permitir a un invitado vigente solicitar un nuevo enlace de acceso
  con su correo, sin revelar si el correo corresponde o no a un invitado registrado.

**Autorización de tratamiento de datos**

- **FR-014**: El sistema NO DEBE permitir el uso de ninguna función, salvo consultar la política,
  autorizarla, rechazarla, cerrar sesión y solicitar supresión, a un usuario sin autorización
  vigente.
- **FR-015**: La autorización DEBE ser explícita (sin opciones preseleccionadas) y registrarse
  con usuario, fecha y hora, versión de la política y resultado (aceptada, rechazada, revocada).
- **FR-016**: La política DEBE presentar la finalidad del tratamiento, los datos recogidos, los
  derechos del titular y los canales para ejercerlos.
- **FR-017**: El sistema DEBE versionar la política; publicar una nueva versión DEBE exigir que
  cada usuario la acepte antes de seguir usando la plataforma.
- **FR-018**: El usuario DEBE poder consultar su autorización vigente y su historial de
  autorizaciones, y revocarla en cualquier momento; la revocación DEBE suspender su acceso.

**Perfil**

- **FR-019**: En el primer ingreso institucional el usuario DEBE completar solo programa
  académico (de un catálogo), semestre, fecha estimada de presentación de Saber Pro y meta
  diaria (casual, regular o intensa).
- **FR-020**: Los invitados DEBEN completar solo nombre, meta diaria y, de forma opcional, fecha
  estimada de presentación.
- **FR-021**: El usuario DEBE poder editar sus datos de perfil propios; los datos que provienen
  del directorio institucional NO DEBEN ser editables en Saber Uli.
- **FR-022**: Si el usuario interrumpe el primer ingreso, el sistema DEBE retomarlo en el paso
  pendiente (autorización o perfil).

**Roles, grupos y cuentas**

- **FR-023**: El sistema DEBE soportar los roles Estudiante, Invitado, Docente, Director de
  programa y Administrador, y permitir que un usuario institucional tenga varios roles
  simultáneamente, con la unión de sus permisos.
- **FR-024**: Solo un Administrador DEBE poder asignar o retirar roles. El rol Invitado es
  exclusivo: un invitado NO DEBE tener otros roles.
- **FR-025**: El sistema DEBE impedir que se retire el rol Administrador al último administrador
  activo.
- **FR-026**: Un Director de programa DEBE estar asociado a uno o varios programas y solo DEBE
  ver información de esos programas, siempre agregada o seudonimizada: NO DEBE ver nombre,
  correo ni ningún otro dato que identifique a un estudiante.
- **FR-027**: El Administrador DEBE poder crear grupos o cohortes, agregar y quitar estudiantes
  institucionales y asociar docentes. Un docente solo DEBE ver el nombre y el progreso de los
  estudiantes de sus grupos; NO DEBE ver su correo ni los datos de estudiantes de otros grupos.
- **FR-028**: El Administrador DEBE poder gestionar el catálogo de programas académicos.
- **FR-029**: El Administrador DEBE poder desactivar y reactivar cuentas; una cuenta desactivada
  NO DEBE poder ingresar y sus sesiones DEBEN terminar.
- **FR-030**: El sistema DEBE negar el acceso a cualquier función no permitida por los roles del
  usuario.

**Derechos del titular**

- **FR-031**: El usuario DEBE poder consultar y descargar todos sus datos personales en un
  formato legible.
- **FR-032**: El usuario DEBE poder solicitar la supresión de su cuenta y datos personales, con
  confirmación explícita; el acceso DEBE terminar de inmediato y la supresión completarse en un
  máximo de 15 días hábiles.
- **FR-033**: Tras la supresión, los registros que deban conservarse (estadísticas de respuestas,
  auditoría) NO DEBEN contener datos que permitan identificar a la persona.
- **FR-034**: El Administrador DEBE poder ver el estado y la fecha límite de cada solicitud de
  supresión.
- **FR-034a**: Cuando el acceso de un invitado vence o se revoca, su cuenta y sus datos DEBEN
  conservarse 90 días; si en ese plazo se renueva su acceso, recupera su progreso. Al cumplirse
  los 90 días sin renovación, el sistema DEBE suprimir automáticamente sus datos personales con
  las mismas reglas de FR-033, y la supresión DEBE quedar auditada.
- **FR-034b**: Una cuenta institucional sin ningún ingreso exitoso durante 1 año DEBE pasar a
  inactiva y sus datos personales DEBEN suprimirse automáticamente con las mismas reglas de
  FR-033; la supresión DEBE quedar auditada.
- **FR-034c**: 30 días antes de una supresión automática (FR-034a o FR-034b), el sistema DEBE
  enviar un correo a la persona que explique la fecha de supresión y cómo evitarla: volver a
  ingresar (institucionales) o pedir la renovación del acceso a quien lo invitó (invitados). Si
  la persona ingresa o se renueva su acceso antes de esa fecha, la supresión se cancela. Si el
  correo no puede entregarse, la supresión sigue su curso en la fecha prevista.
- **FR-034d**: La supresión automática por inactividad (FR-034b) NO DEBE aplicarse al último
  administrador activo; en su lugar, el sistema DEBE registrar el caso en la auditoría, visible
  para los administradores. Una solicitud de supresión
  voluntaria del último administrador activo DEBE rechazarse hasta que otro usuario tenga el rol
  Administrador.
- **FR-034e**: Una invitación que nunca se aceptó DEBE perder el correo y el nombre del invitado
  90 días después de vencer su enlace o de ser revocada.

**Auditoría y sesiones**

- **FR-035**: El sistema DEBE auditar toda acción administrativa sobre usuarios, roles, grupos,
  programas e invitaciones, y todo cambio de autorización, registrando quién, qué, sobre quién y
  cuándo. Los registros de auditoría NO DEBEN poder modificarse ni borrarse desde la aplicación.
- **FR-036**: El sistema DEBE registrar los intentos de ingreso rechazados sin almacenar datos
  personales en los registros técnicos.
- **FR-037**: El usuario DEBE poder cerrar sesión; las sesiones inactivas DEBEN expirar.
- **FR-038**: Un usuario autenticado DEBE poder seguir usando la app sin conexión hasta 7 días
  desde su última validación con conexión; pasado ese plazo DEBE volver a autenticarse con red.
- **FR-039**: Al recuperar la conexión, el sistema DEBE validar que la cuenta sigue activa, que
  el acceso no venció ni fue revocado y que la autorización de datos sigue vigente ANTES de
  sincronizar la actividad hecha sin conexión. Si alguna validación falla, la actividad
  pendiente NO DEBE sincronizarse y el usuario DEBE ver la causa.

### Key Entities *(include if feature involves data)*

- **Usuario**: persona con acceso a Saber Uli. Tipo (institucional o invitado), estado (activo,
  desactivado, vencido, revocado, en supresión), identificador estable externo
  (institucionales), nombre, correo, fecha del último ingreso exitoso (desde la que se cuenta el
  año de conservación de institucionales) y fecha de fin de acceso (invitados, desde la que se
  cuentan los 90 días de conservación).
- **Perfil**: datos de preparación del usuario: programa académico, semestre, fecha estimada de
  presentación, meta diaria. Pertenece a un Usuario.
- **Rol y asignación de rol**: rol de un usuario (Estudiante, Invitado, Docente, Director de
  programa, Administrador), con quién lo asignó y cuándo. Un Director se asocia a programas.
- **Programa académico**: catálogo administrado de programas de la Universidad.
- **Grupo / Cohorte**: conjunto de estudiantes institucionales con uno o varios docentes
  asociados.
- **Invitación**: correo destino, quién invitó, fecha de vencimiento del acceso, estado
  (Enviada, Aceptada, Vencida, Revocada), fechas de envío y aceptación.
- **Enlace de acceso**: credencial de un solo uso y corta duración asociada a un invitado.
- **Versión de la política de tratamiento de datos**: texto, número de versión y fecha de
  vigencia.
- **Autorización**: decisión de un usuario sobre una versión de la política (aceptada,
  rechazada, revocada) con fecha y hora.
- **Solicitud de supresión**: usuario solicitante, fecha, estado y fecha límite.
- **Registro de auditoría**: actor, acción, objeto afectado, fecha y hora; inmutable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un estudiante Unilibre que ingresa por primera vez llega al inicio de su primera
  lección en menos de 1 minuto (autenticación, autorización de datos y perfil incluidos), en el
  90 % de los casos.
- **SC-002**: El 100 % de los usuarios activos tiene una autorización vigente registrada con fecha
  y versión de la política.
- **SC-003**: El 0 % de los intentos de ingreso de invitados vencidos o revocados, o de cuentas
  Microsoft fuera del inquilino Unilibre, tiene éxito.
- **SC-004**: El 100 % de las acciones administrativas sobre usuarios, roles, grupos e
  invitaciones tiene un registro de auditoría.
- **SC-005**: Un administrador envía un lote de 200 invitaciones, con reporte de errores por
  fila, en menos de 5 minutos de trabajo.
- **SC-006**: El 100 % de las solicitudes de supresión se completa en un máximo de 15 días
  hábiles.
- **SC-007**: Un invitado que recibe su invitación ingresa a la plataforma en menos de 2 minutos
  desde que abre el correo.
- **SC-008**: Al menos el 90 % de los usuarios que ven el mensaje de rechazo de cuenta no
  institucional entiende la causa y la alternativa (validado en pruebas con usuarios).

## Assumptions

- Los invitados acceden solo por invitación con enlace de acceso enviado al correo; no hay
  registro abierto. Pueden invitar administradores y docentes (confirmado el 2026-10-05).
- El plazo máximo de acceso para invitaciones enviadas por docentes es de 180 días mientras un
  administrador no configure otro.
- Si el administrador no indica otra cosa, el acceso de un invitado vence a los 90 días de
  enviada la invitación; el enlace de invitación vence a los 7 días y los enlaces de ingreso
  posteriores a los 10 minutos (máximo configurable: 10, por ASVS 2.7.2; enmienda del 2026-10-08).
- Todas las cuentas institucionales, incluidos funcionarios y docentes, entran con rol Estudiante;
  los demás roles los asigna un administrador.
- Los usuarios son mayores de edad; la autorización la otorga el propio titular.
- La revocación de la autorización suspende el acceso pero no borra datos; borrar requiere una
  solicitud de supresión.
- La supresión se completa en un máximo de 15 días hábiles, alineado con los plazos de la
  Ley 1581 de 2012 para reclamos.
- Las sesiones inactivas expiran tras un periodo razonable definido en el plan técnico.
- El catálogo de programas académicos lo carga un administrador; no se integra con sistemas
  académicos en esta funcionalidad.
- La meta diaria se elige aquí, pero su significado (XP por día) se define en la
  funcionalidad 004 (gamificación).
- **Dependencia externa**: la oficina de TI de Unilibre registra la aplicación en el proveedor de
  identidad institucional y entrega sus credenciales y direcciones de retorno.
- **Dependencia externa**: existe un canal de envío de correo para las invitaciones, los enlaces
  de acceso y los avisos de supresión automática.
- El correo institucional de una persona que ya salió del directorio puede no recibir el aviso
  de supresión; se acepta ese riesgo (FR-034c).

## Out of Scope

- Pagos.
- Inicio de sesión con redes sociales.
- Registro abierto al público.
- Integración con sistemas académicos de Unilibre para importar programas o grupos.
