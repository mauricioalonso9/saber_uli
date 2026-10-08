"""T056: semilla y repositorio de parámetros (migraciones 0004 y 0007; data-model §2.15)."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.infrastructure.repositories.settings import SqlAlchemySettingsRepository
from saber_uli.shared.infrastructure.migrations import run_migrations, stamp_migrations
from tests.integration.conftest import UserFactory


async def test_la_migracion_siembra_los_valores_por_defecto(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT key, value FROM identity.settings"))

    assert {row.key: row.value for row in rows}.items() >= {
        "teacher_max_access_days": 180,
        "default_guest_access_days": 90,
        "invitation_link_ttl_days": 7,
        "sign_in_link_ttl_minutes": 10,
    }.items()


async def test_cargar_y_guardar_solo_lo_que_cambia(
    db_session: AsyncSession, user_factory: UserFactory
) -> None:
    admin = await user_factory()
    repo = SqlAlchemySettingsRepository(db_session)
    current = await repo.load()
    assert current == IdentitySettings()

    changed = current.with_changes(teacher_max_access_days=120)
    await repo.save(changed, previous=current, updated_by=admin.id)

    assert await repo.load() == changed
    row = (
        await db_session.execute(
            text("SELECT updated_by FROM identity.settings WHERE key = 'teacher_max_access_days'")
        )
    ).one()
    assert row.updated_by == admin.id
    untouched = (
        await db_session.execute(
            text("SELECT updated_by FROM identity.settings WHERE key = 'sign_in_link_ttl_minutes'")
        )
    ).one()
    assert untouched.updated_by is None


async def test_una_clave_ausente_toma_el_valor_por_defecto(db_session: AsyncSession) -> None:
    await db_session.execute(
        text("UPDATE identity.settings SET key = 'obsoleta' WHERE key = 'invitation_link_ttl_days'")
    )

    loaded = await SqlAlchemySettingsRepository(db_session).load()

    assert loaded.invitation_link_ttl_days == 7


async def _sign_in_ttl_after_0007(engine: AsyncEngine, url: str, stored: int) -> int:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE identity.settings SET value = to_jsonb(CAST(:v AS integer))"
                " WHERE key = 'sign_in_link_ttl_minutes'"
            ),
            {"v": stored},
        )
    # Alembic crea su propio bucle de eventos: se ejecuta en otro hilo.
    await asyncio.to_thread(stamp_migrations, url, "0006")
    await asyncio.to_thread(run_migrations, url)
    async with engine.connect() as conn:
        value = (
            await conn.execute(
                text("SELECT value FROM identity.settings WHERE key = 'sign_in_link_ttl_minutes'")
            )
        ).scalar_one()
    return int(value)


async def test_0007_recorta_el_enlace_de_ingreso_a_10_minutos_y_respeta_valores_menores(
    migrator_engine: AsyncEngine, migrated_database: dict[str, str]
) -> None:
    # ASVS 2.7.2 (T178a): fuera del rango nuevo (5 a 10) los parámetros no cargarían.
    url = migrated_database["migrator"]
    try:
        assert await _sign_in_ttl_after_0007(migrator_engine, url, 15) == 10
        assert await _sign_in_ttl_after_0007(migrator_engine, url, 8) == 8
    finally:
        async with migrator_engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE identity.settings SET value = '10'::jsonb"
                    " WHERE key = 'sign_in_link_ttl_minutes'"
                )
            )
