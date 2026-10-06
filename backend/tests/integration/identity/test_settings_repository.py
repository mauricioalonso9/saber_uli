"""T056: semilla y repositorio de parámetros (migración 0004; data-model §2.15)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.infrastructure.repositories.settings import SqlAlchemySettingsRepository
from tests.integration.conftest import UserFactory


async def test_la_migracion_siembra_los_valores_por_defecto(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT key, value FROM identity.settings"))

    assert {row.key: row.value for row in rows}.items() >= {
        "teacher_max_access_days": 180,
        "default_guest_access_days": 90,
        "invitation_link_ttl_days": 7,
        "sign_in_link_ttl_minutes": 15,
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
