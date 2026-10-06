# ADR 0001: Monolito modular con contextos delimitados

- **Estado**: Aceptado
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/plan.md`, research R-03 y R-04

## Contexto

Saber Uli tiene varios dominios con reglas propias (identidad, banco de ítems, aprendizaje,
gamificación, evaluación, analítica, notificaciones), un equipo pequeño y un despliegue con
Docker Compose en un solo servidor. La constitución (principio II) exige contextos delimitados
con arquitectura hexagonal y prohíbe microservicios sin un ADR justificado con datos.

## Decisión

- Un único backend desplegable (`saber_uli`) con un subpaquete por contexto:
  `shared`, `identity`, `notifications` (creados en 001) y `content`, `learning`,
  `gamification`, `assessment`, `analytics` (creados por su especificación).
- Cada contexto tiene las capas `domain`, `application`, `infrastructure` y `api`. Las
  dependencias apuntan hacia `domain`.
- Un contexto solo usa a otro a través de su fachada `application` pública o reaccionando a sus
  eventos de dominio; nunca lee sus tablas. Cada contexto tiene su propio esquema de PostgreSQL.
- Las reglas se verifican en CI con `import-linter`.

## Consecuencias

- Un solo despliegue, una sola base de datos y transacciones locales simples.
- Los límites entre contextos son explícitos y comprobables; extraer un contexto como servicio
  en el futuro es posible porque ya se comunica por fachada o eventos.
- Requiere disciplina: cualquier atajo entre contextos falla en CI.

## Alternativas descartadas

- **Microservicios**: costo operativo desproporcionado para el tamaño del equipo y la carga.
- **Monolito por capas sin contextos**: acopla dominios y dificulta la evolución independiente.
