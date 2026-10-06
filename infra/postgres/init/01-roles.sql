-- Roles de base de datos con mínimo privilegio (research R-07, constitución IX, FR-035).
--
-- La imagen oficial de PostgreSQL ejecuta este archivo una sola vez, al crear el volumen, con
-- el superusuario y `psql -v ON_ERROR_STOP=1`. Las contraseñas se leen del entorno con
-- `\getenv`; si falta alguna o es corta, el script falla y el contenedor no arranca.
--
--   saber_migrator  DDL: dueño de los esquemas y tablas; solo lo usa el servicio `migrate`.
--   saber_app       DML para `api`, `worker` y `beat`; sus permisos sobre tablas los otorga la
--                   migración 0003_identity_grants (ALTER DEFAULT PRIVILEGES de saber_migrator).
--   saber_bi        solo lectura del esquema `analytics` (spec 008); aquí no recibe objetos.
--
-- Ningún servicio usa el superusuario de la imagen.

\getenv saber_migrator_password SABER_MIGRATOR_PASSWORD
\getenv saber_app_password SABER_APP_PASSWORD
\getenv saber_bi_password SABER_BI_PASSWORD

\if :{?saber_migrator_password}
\else
DO $$ BEGIN RAISE EXCEPTION 'Falta la variable de entorno SABER_MIGRATOR_PASSWORD'; END $$;
\endif
\if :{?saber_app_password}
\else
DO $$ BEGIN RAISE EXCEPTION 'Falta la variable de entorno SABER_APP_PASSWORD'; END $$;
\endif
\if :{?saber_bi_password}
\else
DO $$ BEGIN RAISE EXCEPTION 'Falta la variable de entorno SABER_BI_PASSWORD'; END $$;
\endif

SELECT length(:'saber_migrator_password') >= 16
   AND length(:'saber_app_password') >= 16
   AND length(:'saber_bi_password') >= 16 AS saber_passwords_ok
\gset
\if :saber_passwords_ok
\else
DO $$ BEGIN RAISE EXCEPTION 'Las contraseñas de saber_migrator, saber_app y saber_bi deben tener al menos 16 caracteres'; END $$;
\endif

SET password_encryption = 'scram-sha-256';

CREATE ROLE saber_migrator LOGIN PASSWORD :'saber_migrator_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;
CREATE ROLE saber_app LOGIN PASSWORD :'saber_app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;
CREATE ROLE saber_bi LOGIN PASSWORD :'saber_bi_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;

\unset saber_migrator_password
\unset saber_app_password
\unset saber_bi_password

-- Solo estos tres roles se conectan a la base de la aplicación.
REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE :"DBNAME" TO saber_app;
GRANT CONNECT ON DATABASE :"DBNAME" TO saber_bi;
-- CREATE en la base permite a saber_migrator crear los esquemas `shared`, `identity`, etc.
GRANT CONNECT, CREATE, TEMPORARY ON DATABASE :"DBNAME" TO saber_migrator;

-- Nadie crea objetos en `public` (allí solo viven las extensiones).
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO saber_migrator, saber_app, saber_bi;

-- Límites de protección: una consulta o transacción colgada no bloquea la API.
ALTER ROLE saber_app SET statement_timeout = '30s';
ALTER ROLE saber_app SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE saber_bi SET statement_timeout = '5min';
ALTER ROLE saber_bi SET default_transaction_read_only = on;
