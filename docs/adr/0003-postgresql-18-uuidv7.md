# ADR 0003: PostgreSQL 18 con claves uuidv7 y un esquema por contexto

- **Estado**: Aceptado
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/plan.md`, research R-06 y R-07

## Contexto

La decisión de proyecto fija PostgreSQL 18. Se necesitan claves que no revelen volumen, sean
ordenables en el tiempo y no requieran coordinación; además, mínimo privilegio (principio IX) y
separación de datos por contexto (principio II).

## Decisión

- Imagen oficial `postgres:18`; el volumen se monta en `/var/lib/postgresql` (cambio de la
  versión 18).
- Claves primarias `uuid DEFAULT uuidv7()` (función nativa de PostgreSQL 18). Las entidades con
  identificador de negocio (por ejemplo, ítems `LC-0001`) lo conservan como clave única aparte.
- Un esquema por contexto (`identity`, `shared`, y los de cada especificación futura).
- SQLAlchemy 2 asíncrono con asyncpg; un solo historial de Alembic.
- Roles de base de datos: `saber_migrator` (DDL), `saber_app` (DML), `saber_bi` (solo lectura del
  esquema `analytics`). Las tablas de solo inserción (auditoría, autorizaciones) no conceden
  `UPDATE` ni `DELETE` a `saber_app`.
- Extensiones: `citext` y `pg_stat_statements`.

## Consecuencias

- Inserciones con buena localidad en índices B-tree gracias a uuidv7.
- La inmutabilidad de la auditoría la garantiza la base de datos, no solo el código.
- Las pruebas de integración usan `postgres:18` real (Testcontainers).

## Alternativas descartadas

- **Claves `bigserial`**: revelan volumen y obligan a coordinar en importaciones.
- **UUID v4**: fragmentan los índices.
- **Base de datos por contexto**: complejidad operativa sin necesidad en un monolito.
