"""T024: prueba de humo de los contenedores de integración (PostgreSQL 18 y Redis 8)."""

import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


async def test_saber_app_se_conecta_y_consulta(db_session: AsyncSession) -> None:
    assert (await db_session.execute(text("SELECT current_user"))).scalar_one() == "saber_app"
    assert (await db_session.execute(text("SELECT 1"))).scalar_one() == 1


async def test_extensiones_instaladas(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT extname FROM pg_extension"))

    assert {"citext", "pg_stat_statements"} <= set(rows.scalars())


async def test_saber_app_no_puede_crear_tablas(app_engine: AsyncEngine) -> None:
    async with app_engine.connect() as conn:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await conn.execute(text("CREATE TABLE public.x (id int)"))


async def test_saber_migrator_si_puede_crear_esquemas(migrator_engine: AsyncEngine) -> None:
    async with migrator_engine.connect() as conn:
        await conn.execute(text("CREATE SCHEMA humo"))
        await conn.execute(text("DROP SCHEMA humo"))
        await conn.rollback()


async def test_db_session_revierte_al_terminar(
    db_session: AsyncSession, migrator_engine: AsyncEngine
) -> None:
    # La sesión de la prueba trabaja dentro de una transacción que se revierte al final.
    await db_session.execute(text("CREATE TEMP TABLE t (id int)"))
    await db_session.execute(text("INSERT INTO t VALUES (1)"))
    await db_session.commit()  # confirma solo el savepoint, no la transacción externa

    assert (await db_session.execute(text("SELECT count(*) FROM t"))).scalar_one() == 1


async def test_redis_responde(redis_client: Redis) -> None:
    assert await redis_client.ping() is True
    await redis_client.set("humo", "1")
    assert await redis_client.get("humo") == b"1"
