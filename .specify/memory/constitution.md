<!--
Sync Impact Report
- Versión: 1.0.0 → 1.0.1 (PATCH: aclaraciones de alcance, sin quitar exigencias al código)
- Principios modificados:
  IV. Pruebas primero: se precisa que la regla cubre toda tarea de código, incluida la
      infraestructura ejecutable, y que las tareas solo de documentación quedan exentas.
- Secciones modificadas:
  Flujo de trabajo y puertas de calidad (Definición de Terminado): la carga del banco inicial
  es obligatoria a partir de la funcionalidad 002, que la implementa.
- Secciones añadidas / eliminadas: ninguna
- Origen: hallazgos C1 y C2 de /speckit.analyze sobre specs/001-identidad-acceso
- Plantillas: no se modifican (leen la constitución en tiempo de ejecución)
- TODO diferidos: ninguno
-->

# Constitución de Saber Uli

Saber Uli es un aplicativo web gamificado (estilo Duolingo), instalable como PWA en celulares,
para que la comunidad de la Universidad Libre (Colombia) se prepare para los cinco módulos de
competencias genéricas de las pruebas Saber Pro del ICFES: Lectura crítica, Razonamiento
cuantitativo, Competencias ciudadanas, Comunicación escrita e Inglés.

En este documento, DEBE / NO DEBE indican obligaciones verificables; DEBERÍA indica una
práctica recomendada cuya omisión se justifica por escrito.

## Principios fundamentales

### I. Especificación primero

- Ningún código DEBE escribirse sin una especificación aprobada en `specs/`.
- La especificación es la fuente de verdad: todo cambio de comportamiento DEBE empezar por
  modificar la especificación.
- Las especificaciones DEBEN describir el qué y el porqué; NO DEBEN mencionar tecnología
  (lenguajes, frameworks, bases de datos, librerías).

**Justificación:** separar el problema de la solución mantiene alineados a docentes, producto y
desarrollo, y evita que el código se convierta en la única documentación del comportamiento.

### II. Monolito modular con contextos delimitados (DDD)

- El sistema DEBE ser un monolito modular organizado en contextos delimitados.
- Cada contexto DEBE tener las capas `domain` / `application` / `infrastructure` / `api`
  (arquitectura hexagonal); las dependencias DEBEN apuntar hacia el dominio.
- Un contexto NO DEBE acceder a las tablas de otro; se comunica solo mediante servicios de
  aplicación o eventos de dominio.
- NO DEBEN introducirse microservicios sin un ADR que lo justifique con datos.

**Justificación:** ofrece límites claros y evolución independiente de cada contexto sin el
costo operativo de un sistema distribuido, adecuado al tamaño del equipo y del despliegue.

### III. Contrato primero

- El contrato OpenAPI 3.1 de cada funcionalidad DEBE definirse en el plan antes de implementar.
- El cliente del frontend DEBE generarse desde el contrato; no se escriben llamadas a la API a
  mano.
- Los cambios incompatibles del contrato DEBEN publicarse como una nueva versión de la API.

**Justificación:** un contrato único y verificable evita divergencias entre backend y frontend
y permite trabajar en paralelo y probar el contrato de forma automática.

### IV. Pruebas primero (TDD, NO NEGOCIABLE)

- Para cada tarea de código (dominio, aplicación, API, interfaz e infraestructura ejecutable:
  Dockerfiles, Compose, Nginx, migraciones, CI) DEBEN escribirse primero las pruebas
  automatizadas, y DEBE verificarse que fallan antes de implementar. Las tareas que solo
  producen documentación quedan exentas.
- Pirámide obligatoria: unitarias de dominio; integración contra PostgreSQL 18 real
  (Testcontainers); pruebas de contrato contra OpenAPI; extremo a extremo de los flujos
  críticos.
- La cobertura mínima DEBE ser del 80 % en las capas de dominio y aplicación.

**Justificación:** las reglas de puntaje, rachas, sincronización sin conexión y versionado de
ítems son sutiles; las pruebas previas fijan el comportamiento esperado y evitan regresiones.

### V. Protección de datos personales

- El sistema DEBE cumplir la Ley 1581 de 2012 y sus decretos reglamentarios: autorización
  expresa del titular, finalidad declarada, minimización y derechos de consulta, rectificación
  y supresión.
- Los logs NO DEBEN contener datos personales.
- Los datos analíticos DEBEN seudonimizarse.
- Del directorio institucional solo DEBEN tomarse los datos estrictamente necesarios.

**Justificación:** la plataforma trata datos de estudiantes y personal universitario; el
cumplimiento legal y la confianza de la comunidad son condiciones para operar.

### VI. Integridad académica y propiedad intelectual

- Los ítems DEBEN ser originales y alinearse a la estructura publicada por el ICFES
  (competencias, afirmaciones, evidencias y partes de Inglés).
- NO DEBEN reproducirse preguntas ni cuadernillos del ICFES.
- Todo ítem, incluidos los generados con IA, DEBE pasar por revisión humana antes de
  publicarse.
- Toda estimación de puntaje DEBE rotularse como "estimación no oficial".

**Justificación:** protege a la Universidad de infracciones de propiedad intelectual y a los
estudiantes de contenido erróneo o de expectativas falsas sobre su resultado oficial.

### VII. La gamificación sirve al aprendizaje

- Cada respuesta DEBE mostrar retroalimentación explicativa.
- Las mecánicas de juego (XP, rachas, ligas) DEBEN reforzar la práctica constante y NO DEBEN
  bloquear nunca el acceso al estudio.
- NO DEBEN usarse patrones oscuros ni compras dentro de la aplicación.

**Justificación:** el objetivo es mejorar el desempeño en Saber Pro; el juego es un medio para
sostener el hábito, no un fin ni un mecanismo de presión o monetización.

### VIII. Móvil primero, accesible e inclusivo

- La experiencia principal DEBE ser una PWA instalable que funcione en celulares de gama media.
- La aplicación DEBE tolerar conexiones lentas o intermitentes: práctica sin conexión con
  sincronización posterior.
- La interfaz DEBE cumplir WCAG 2.2 nivel AA.
- El idioma por defecto DEBE ser el español de Colombia.

**Justificación:** la mayoría de los estudiantes practicará desde el celular, en trayectos y
con datos limitados; la accesibilidad garantiza que nadie de la comunidad quede excluido.

### IX. Seguridad por diseño

- La referencia de seguridad DEBE ser OWASP ASVS nivel 2.
- La autenticación institucional DEBE delegarse en Microsoft Entra ID (OIDC); las cuentas de
  invitado DEBEN tener controles propios.
- Los secretos DEBEN entregarse solo por variables de entorno y nunca versionarse.
- DEBEN aplicarse mínimo privilegio, limitación de peticiones y escaneo de dependencias en CI.

**Justificación:** el sistema maneja identidades institucionales y datos personales; los
controles deben diseñarse desde el inicio, no añadirse al final.

### X. Reproducibilidad y operación (12-factor)

- Todo el sistema DEBE levantar con `docker compose up`.
- DEBEN usarse migraciones versionadas y configuración por entorno.
- Todos los servicios DEBEN exponer health checks y emitir logs estructurados en JSON.
- Las imágenes DEBEN ejecutarse sin root.

**Justificación:** entornos idénticos en desarrollo y producción reducen fallas de despliegue
y facilitan que la oficina de TI opere el sistema.

### XI. Simplicidad

- YAGNI: solo DEBE construirse lo que la especificación pide.
- Toda dependencia nueva DEBE justificarse en `research.md`.
- Toda decisión arquitectónica relevante DEBE registrarse como ADR en `docs/adr/`.
- NO DEBE usarse PHP en ningún componente.

**Justificación:** menos piezas significan menos mantenimiento y superficie de ataque; los ADR
preservan el porqué de las decisiones para quienes lleguen después.

## Restricciones de dominio y tecnología

- **Alcance:** solo los cinco módulos genéricos de Saber Pro.
- **Estructura oficial del examen** (Guía de orientación Saber Pro 2026-2, ICFES), que la app
  DEBE respetar en simulacros y estimaciones: Comunicación escrita 1 tarea abierta,
  Razonamiento cuantitativo 30, Lectura crítica 30, Competencias ciudadanas 30 e Inglés 45
  preguntas; sesión de 4 h 40 min; puntaje de 0 a 300 por módulo y puntaje global igual al
  promedio de los cinco.
- **Acceso:** comunidad Unilibre con SSO de Microsoft 365 (Entra ID/OIDC) e invitados por
  invitación.
- **Banco de preguntas:** el banco inicial (`backend/seeds/banco_inicial_saber_uli.json`) se
  incluye en estado `en_revision`; la aplicación DEBE permitir cargar ítems nuevos y actualizar
  los existentes.
- **Stack:** backend en Python (FastAPI); frontend React + TypeScript como PWA; base de datos
  PostgreSQL 18; despliegue con Docker (Docker Engine + Compose v2).
- **Convenciones:** código en inglés; textos de interfaz, documentación y ADR en español.

## Flujo de trabajo y puertas de calidad

- **Ciclo SDD por funcionalidad** (una especificación por funcionalidad, `NNN-nombre`):
  `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` →
  `/speckit.analyze` → `/speckit.implement` → revisión.
- **Roles de los modelos:** Opus especifica, planea, analiza y revisa; Qwen implementa las
  tareas asignadas, las marca como "lista para revisión" y NO DEBE cambiar el contrato OpenAPI,
  el modelo de datos ni los ADR (registra dudas como decisiones pendientes).
- **Puerta del plan:** `/speckit.plan` DEBE verificar el cumplimiento de cada principio y
  justificar por escrito cualquier excepción.
- **Puerta del análisis:** `/speckit.analyze` DEBE reportar violaciones a la constitución; una
  violación abierta bloquea la implementación.
- **Definición de Terminado:** criterios de aceptación con prueba automatizada; suites en verde
  y cobertura ≥ 80 % en dominio y aplicación; contrato verificado contra la implementación;
  `docker compose up` funcional desde cero con las migraciones y semillas que la funcionalidad
  defina (la carga del banco inicial es obligatoria a partir de la funcionalidad 002); PWA instalable y usable
  en viewport móvil; sin hallazgos críticos de lint, tipos, accesibilidad, rendimiento ni
  seguridad; ADR y documentación actualizados; revisión de Opus aprobada.

## Gobernanza

- Esta constitución prevalece sobre cualquier otra práctica, guía o convención del proyecto.
- Las enmiendas DEBEN hacerse por pull request, con la justificación del cambio, la
  actualización de la versión y el registro del cambio en el informe de impacto.
- Versionado semántico de la constitución:
  - MAYOR: eliminación o redefinición incompatible de un principio o regla de gobernanza.
  - MENOR: principio o sección nuevos, o ampliación material de una guía.
  - PARCHE: aclaraciones, redacción o correcciones sin cambio semántico.
- `/speckit.plan` y `/speckit.analyze` DEBEN verificar el cumplimiento de cada principio; toda
  revisión de código DEBE comprobarlo también. La complejidad adicional DEBE justificarse.
- La guía operativa de desarrollo vive en `CLAUDE.md` y en `specs/<feature-activa>/tasks.md`.

**Versión**: 1.0.1 | **Ratificada**: 2026-10-05 | **Última enmienda**: 2026-10-06
