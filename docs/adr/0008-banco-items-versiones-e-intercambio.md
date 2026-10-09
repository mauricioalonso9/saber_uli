# ADR 0008: Banco de ítems con versiones inmutables y formato de intercambio único

- **Estado**: Aceptado
- **Fecha**: 2026-10-09
- **Origen**: `specs/002-banco-items/plan.md`, research R-02, R-03, R-05, R-06 y R-07

## Contexto

Los ítems cambian con el tiempo: los docentes los corrigen, el ICFES publica guías nuevas y cada
versión de la aplicación puede traer un banco inicial actualizado. Al mismo tiempo, cada
respuesta de un estudiante (003) debe seguir apuntando a la pregunta exacta que respondió, y las
estadísticas se reinician por versión. El banco entra y sale de la aplicación por tres caminos:
la carga del banco inicial, la importación de los docentes y la exportación. Ninguno debe
duplicar ni perder trabajo.

## Decisión

- **Versiones inmutables.**
  - Un ítem tiene un código de negocio estable (`LC-0001`) y versiones numeradas.
  - Una versión Publicada o Retirada no se modifica nunca; solo se edita la versión abierta
    (Borrador o En revisión).
  - La base garantiza, con índices únicos parciales, a lo sumo una versión Publicada y una
    abierta por ítem.
  - Las respuestas referencian la versión.
- **Contextos versionados.**
  - Cada versión de ítem fija la versión de su contexto.
  - Editar un contexto crea una versión nueva del contexto. Los ítems publicados que lo usan
    reciben una versión nueva que pasa por revisión.
- **Un solo formato de intercambio.**
  - El JSON del banco inicial (`esquema_version: "1.0"`) es el formato de carga, importación y
    exportación.
  - Su JSON Schema (`backend/schemas/banco_items.schema.json`) se genera desde los mismos
    modelos que validan.
  - La plantilla XLSX es una vista reducida del mismo formato, solo para ítems de selección.
- **Huellas para decidir sin ambigüedad.**
  - `content_hash`, sobre la forma canónica del contenido: "sin cambios" no crea versión.
  - `fingerprint`, sobre el texto normalizado: detecta duplicados con otro código.
  - `seed_hash`, sobre el ítem tal como vino en el banco inicial: distingue "cambió el
    archivo" de "cambió un docente".
- **Importar en dos pasos.**
  - Primero se valida y se muestra la vista previa; después se confirma en una sola
    transacción.
  - El banco inicial usa el mismo validador y se carga en cada despliegue (servicio
    `migrate`), de forma idempotente.

## Consecuencias

- La historia académica es exacta: ninguna edición altera lo que un estudiante respondió.
- Reimportar o redesplegar es seguro: los mismos datos producen cero cambios.
- El banco crece en filas de versiones. A la escala prevista (10 000 ítems con pocas versiones
  cada uno) eso no es un problema de rendimiento.
- Cualquier cambio del formato de intercambio exige subir `esquema_version` y mantener la lectura
  de la versión anterior.

## Alternativas descartadas

- **Editar en el lugar con un registro de cambios**: las respuestas históricas perderían la
  versión exacta.
- **Event sourcing completo**: más complejo de lo que piden los requisitos (principio XI).
- **Formatos distintos para carga, importación y exportación**: tres validadores que divergen y
  archivos exportados que no se pueden reimportar.
- **Carga del banco inicial como migración de datos**: mezcla esquema y contenido y no permite
  entregar ítems nuevos en versiones posteriores.
