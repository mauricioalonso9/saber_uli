"""Ejecución de las migraciones de Alembic por código (research R-06).

La usan `saber-uli migrate` (servicio `migrate` de Compose) y la fixture `migrated_database` de
las pruebas. No necesita `alembic.ini`: la configuración se arma aquí. Debe llamarse desde
código síncrono, porque `migrations/env.py` crea su propio bucle de eventos.
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def migrations_dir() -> Path:
    """`SABER_MIGRATIONS_DIR` (imagen Docker: /app/migrations) o `backend/migrations`."""
    configured = os.environ.get("SABER_MIGRATIONS_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[4] / "migrations"


def _config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(migrations_dir()))
    config.attributes["url"] = url
    return config


def run_migrations(url: str, revision: str = "head") -> None:
    """Aplica las migraciones hasta `revision` con la URL del rol saber_migrator."""
    command.upgrade(_config(url), revision)


def downgrade_migrations(url: str, revision: str) -> None:
    """Revierte hasta `revision` (por ejemplo `base`). Solo para pruebas y operación manual."""
    command.downgrade(_config(url), revision)
