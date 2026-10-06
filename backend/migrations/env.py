"""Entorno de Alembic (T026; research R-06).

- Un único historial para todo el monolito; cada contexto tiene su esquema (`shared`,
  `identity`…) y `alembic_version` vive en `shared`.
- La URL viene de `config.attributes["url"]` (saber_uli.shared.infrastructure.migrations) o de
  `MIGRATION_DATABASE_URL`. Nunca de la configuración completa de la aplicación: el servicio
  migrate solo tiene la URL del rol saber_migrator (R-07).
- Solo modo en línea y asíncrono (asyncpg).
"""

import asyncio
import os

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from saber_uli.shared.infrastructure.db import Base

# Cada contexto importa aquí sus modelos ORM para que el autogenerado los vea.
# T044 agregará: import saber_uli.identity.infrastructure.orm

config = context.config
target_metadata = Base.metadata

# Esquemas propios del monolito; el autogenerado ignora el resto (por ejemplo `public`).
OWNED_SCHEMAS = frozenset({"shared", "identity"})
VERSION_SCHEMA = "shared"


def _url() -> str:
    url = config.attributes.get("url") or os.environ.get("MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError("Falta MIGRATION_DATABASE_URL (rol saber_migrator).")
    return str(url)


def include_name(name: str | None, type_: str, _parent_names: object) -> bool:
    if type_ == "schema":
        return name in OWNED_SCHEMAS
    return True


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=VERSION_SCHEMA,
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            # `alembic_version` vive en `shared`: el esquema debe existir antes de migrar.
            await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {VERSION_SCHEMA}"))
            await connection.commit()
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise NotImplementedError("Saber Uli no genera SQL fuera de línea; use `saber-uli migrate`.")

asyncio.run(run_migrations_online())
