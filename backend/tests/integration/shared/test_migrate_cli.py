"""T026: `saber-uli migrate` con el rol saber_migrator (research R-06, R-07)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from saber_uli.shared.infrastructure.migrations import migrations_dir


def migrate(url: str | None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "MIGRATION_DATABASE_URL"}
    if url is not None:
        env["MIGRATION_DATABASE_URL"] = url
    return subprocess.run(
        [sys.executable, "-m", "saber_uli.cli", "migrate"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def password(url: str) -> str:
    secret = make_url(url).password
    assert secret
    return secret


async def test_migrate_es_idempotente_y_crea_el_esquema_shared(
    database_urls: dict[str, str],
) -> None:
    url = database_urls["migrator"]
    for _ in range(2):
        result = migrate(url)
        assert result.returncode == 0, result.stderr
        assert password(url) not in result.stdout + result.stderr

    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        schemas = await conn.execute(
            text("SELECT nspname FROM pg_namespace WHERE nspname = 'shared'")
        )
        assert schemas.scalar_one() == "shared"
    await engine.dispose()


def test_saber_app_no_puede_migrar(database_urls: dict[str, str]) -> None:
    url = database_urls["app"]
    result = migrate(url)

    assert result.returncode == 1
    assert password(url) not in result.stdout + result.stderr


def test_sin_la_variable_sale_con_2() -> None:
    result = migrate(None)

    assert result.returncode == 2
    assert "MIGRATION_DATABASE_URL" in result.stderr


def test_ubicacion_de_las_migraciones(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SABER_MIGRATIONS_DIR", raising=False)
    assert migrations_dir() == Path(__file__).resolve().parents[3] / "migrations"

    monkeypatch.setenv("SABER_MIGRATIONS_DIR", "/app/migrations")
    assert migrations_dir() == Path("/app/migrations")
