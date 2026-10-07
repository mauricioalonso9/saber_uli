"""T083: semilla de la política de tratamiento de datos (migración 0005; data-model §2.10)."""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.shared.infrastructure.migrations import run_migrations, stamp_migrations

POLICY_FILE = Path(__file__).resolve().parents[3] / "seeds" / "politica_tratamiento_datos_v1.md"


async def test_tras_migrar_existe_la_version_1_0_vigente_con_el_texto_de_la_semilla(
    db_session: AsyncSession,
) -> None:
    row = (
        await db_session.execute(
            text(
                """SELECT title, body_markdown, effective_from <= now() AS vigente, published_by
                   FROM identity.policy_versions WHERE version = '1.0'"""
            )
        )
    ).one()

    assert row.body_markdown == POLICY_FILE.read_text(encoding="utf-8")
    assert row.title == "Política de tratamiento de datos personales de Saber Uli"
    assert row.vigente is True
    assert row.published_by is None


async def test_volver_a_migrar_no_duplica_la_version_1_0(
    db_session: AsyncSession, migrated_database: dict[str, str]
) -> None:
    # Se vuelve a aplicar 0005 sobre una base que ya tiene la versión 1.0.
    stamp_migrations(migrated_database["migrator"], "0004")
    run_migrations(migrated_database["migrator"])

    count = (
        await db_session.execute(
            text("SELECT count(*) FROM identity.policy_versions WHERE version = '1.0'")
        )
    ).scalar_one()
    assert count == 1
