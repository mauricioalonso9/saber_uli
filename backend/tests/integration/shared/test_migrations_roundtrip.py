"""T028: las migraciones se revierten hasta `base` y se vuelven a aplicar sin error."""

from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import create_async_engine

from saber_uli.shared.infrastructure.migrations import downgrade_migrations, run_migrations

COUNT_TABLES = """
    SELECT count(*) FROM information_schema.tables
    WHERE table_schema IN ('identity', 'shared') AND table_name <> 'alembic_version'
"""


async def count_tables(url: str) -> int:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        total = (await conn.execute(text(COUNT_TABLES))).scalar_one()
    await engine.dispose()
    return int(total)


async def test_downgrade_base_y_upgrade_head(migrated_database: dict[str, str]) -> None:
    url = migrated_database["migrator"]
    before = await count_tables(url)
    assert before > 0

    try:
        downgrade_migrations(url, "base")
        assert await count_tables(url) == 0
    finally:
        # Deja la base como la esperan las demás pruebas de la sesión.
        run_migrations(url)

    assert await count_tables(url) == before
