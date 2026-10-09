-- Extensiones de la base de la aplicación (research R-07).
--
--   citext              correos sin distinguir mayúsculas (data-model.md).
--   pg_stat_statements  observabilidad de consultas (research R-32). Requiere que el servicio
--                       `db` arranque con `-c shared_preload_libraries=pg_stat_statements`.
--
-- Se crean aquí con el superusuario para que saber_migrator no necesite privilegios para ello.

CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;
