"""T011: permisos de `saber_app` sobre el esquema `content` (data-model §2.14; FR-047).

La base de datos, no solo el código, garantiza que la historia, las imágenes, las versiones de
contexto, las exportaciones, los cambios de taxonomía y las cargas del banco inicial sean de solo
inserción, y que de una importación solo cambien su estado y su resultado.
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

APPEND_ONLY = (
    "content.item_events",
    "content.context_versions",
    "content.media",
    "content.exports",
    "content.taxonomy_changes",
    "content.seed_loads",
)


@pytest.fixture
async def app(migrated_database: dict[str, str]) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(migrated_database["app"], poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


async def run(conn: AsyncConnection, sql: str, **params: Any) -> Any:
    return await conn.execute(text(sql), params)


async def denied(conn: AsyncConnection, sql: str, **params: Any) -> None:
    with pytest.raises(DBAPIError, match=r"permission denied|must be owner"):
        async with conn.begin_nested():
            await run(conn, sql, **params)


async def allowed(conn: AsyncConnection, sql: str, **params: Any) -> None:
    async with conn.begin_nested():
        await run(conn, sql, **params)


@pytest.fixture
async def records(app: AsyncConnection) -> dict[str, UUID]:
    """Una fila de cada tabla, creada por saber_app (prueba también los INSERT)."""
    ids: dict[str, UUID] = {}
    await run(
        app,
        """INSERT INTO content.modules (code, name, question_type, options_per_item,
               exam_questions, bank_target, position)
           VALUES ('LC', 'Lectura crítica', 'selection', 4, 30, 150, 1)""",
    )
    ids["node"] = (
        await run(
            app,
            """INSERT INTO content.taxonomy_nodes (module_code, kind, code, name, position)
               VALUES ('LC', 'competence', 'LC-C9', 'Competencia', 1) RETURNING id""",
        )
    ).scalar_one()
    ids["media"] = (
        await run(
            app,
            """INSERT INTO content.media (sha256, content_type, width, height, size_bytes, data,
                   created_by) VALUES ('\\x09', 'image/png', 1, 1, 1, '\\x00', uuidv7())
               RETURNING id""",
        )
    ).scalar_one()
    ids["context"] = (
        await run(
            app,
            """INSERT INTO content.contexts (code, module_code)
               VALUES ('LC-CTX-9', 'LC') RETURNING id""",
        )
    ).scalar_one()
    ids["context_version"] = (
        await run(
            app,
            """INSERT INTO content.context_versions (context_id, number, kind, title, body_md,
                   origin, content_hash) VALUES (:c, 1, 'text', 'T', 'x', 'teacher', '\\x01')
               RETURNING id""",
            c=ids["context"],
        )
    ).scalar_one()
    ids["item"] = (
        await run(
            app,
            """INSERT INTO content.items (code, module_code, kind, origin)
               VALUES ('LC-9999', 'LC', 'selection', 'teacher') RETURNING id""",
        )
    ).scalar_one()
    ids["version"] = (
        await run(
            app,
            """INSERT INTO content.item_versions (item_id, number, state, difficulty, stem_md,
                   explanation_md, content_hash, fingerprint)
               VALUES (:i, 1, 'draft', 'low', 'E', 'X', '\\x01', '\\x02') RETURNING id""",
            i=ids["item"],
        )
    ).scalar_one()
    ids["event"] = (
        await run(
            app,
            """INSERT INTO content.item_events (item_id, version_id, type, occurred_at)
               VALUES (:i, :v, 'created', now()) RETURNING id""",
            i=ids["item"],
            v=ids["version"],
        )
    ).scalar_one()
    ids["import"] = (
        await run(
            app,
            """INSERT INTO content.imports (created_by, created_at, source_name, format,
                   file_sha256, expires_at, summary, rows)
               VALUES (uuidv7(), now(), 'banco.json', 'json', '\\x01', now(), '{}', '[]')
               RETURNING id""",
        )
    ).scalar_one()
    for sql in (
        """INSERT INTO content.exports (created_by, created_at, format, filter, version_choice,
               item_count) VALUES (uuidv7(), now(), 'json', '{}', 'published', 0)""",
        """INSERT INTO content.taxonomy_changes (changed_by, changed_at, target, target_id,
               action) VALUES (uuidv7(), now(), 'node', 'LC-C9', 'created')""",
        """INSERT INTO content.seed_loads (loaded_at, file_sha256, schema_version, summary)
           VALUES (now(), '\\x01', '1.0', '{}')""",
    ):
        await run(app, sql)
    return ids


@pytest.mark.parametrize("table", APPEND_ONLY)
async def test_tablas_de_solo_insercion(
    app: AsyncConnection, records: dict[str, UUID], table: str
) -> None:
    # `table` sale de la constante APPEND_ONLY, no de datos externos.
    await denied(app, f"UPDATE {table} SET id = id")  # noqa: S608
    await denied(app, f"DELETE FROM {table}")  # noqa: S608


async def test_las_versiones_de_item_se_actualizan_pero_no_se_borran(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await allowed(
        app,
        "UPDATE content.item_versions SET stem_md = 'Nuevo' WHERE id = :v",
        v=records["version"],
    )
    await denied(app, "DELETE FROM content.item_versions WHERE id = :v", v=records["version"])
    await denied(app, "DELETE FROM content.items WHERE id = :i", i=records["item"])


async def test_de_una_importacion_solo_cambian_el_estado_y_el_resultado(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await allowed(
        app,
        """UPDATE content.imports SET status = 'expired', payload = NULL, target_state = 'draft',
               originality_declared = false, confirmed_at = NULL, result = '{}' WHERE id = :i""",
        i=records["import"],
    )
    await denied(app, "UPDATE content.imports SET rows = '[]' WHERE id = :i", i=records["import"])
    await denied(
        app, "UPDATE content.imports SET created_by = uuidv7() WHERE id = :i", i=records["import"]
    )
    await denied(app, "DELETE FROM content.imports WHERE id = :i", i=records["import"])


async def test_una_categoria_sin_uso_se_puede_borrar(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await allowed(app, "DELETE FROM content.taxonomy_nodes WHERE id = :n", n=records["node"])


async def test_las_estadisticas_se_reemplazan(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await allowed(
        app,
        """INSERT INTO content.item_version_stats (version_id, first_responses, computed_at)
           VALUES (:v, 0, now())""",
        v=records["version"],
    )
    await allowed(
        app, "DELETE FROM content.item_version_stats WHERE version_id = :v", v=records["version"]
    )


async def test_saber_app_no_cambia_la_estructura(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await denied(app, "ALTER TABLE content.items ADD COLUMN x int")
    await denied(app, "TRUNCATE content.item_events")
