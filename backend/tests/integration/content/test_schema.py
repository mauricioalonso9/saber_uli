"""T009: esquema `content` (data-model §2; research R-02, R-06, R-11, R-12).

Se prueba con `saber_migrator`, dueño del esquema, dentro de una transacción que se revierte: los
permisos de `saber_app` son de 0009 y tienen su propia prueba (T011).
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

TABLES = {
    "modules",
    "taxonomy_nodes",
    "rubrics",
    "media",
    "contexts",
    "context_versions",
    "items",
    "item_versions",
    "item_events",
    "imports",
    "exports",
    "taxonomy_changes",
    "seed_loads",
    "item_version_stats",
}


@pytest.fixture
async def conn(
    migrator_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[AsyncConnection]:
    async with migrator_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


async def scalar(conn: AsyncConnection, sql: str, **params: Any) -> Any:
    return (await conn.execute(text(sql), params)).scalar_one()


async def violates(conn: AsyncConnection, sql: str, **params: Any) -> str:
    """Ejecuta en un savepoint y devuelve el nombre de la restricción violada."""
    savepoint = await conn.begin_nested()
    try:
        await conn.execute(text(sql), params)
    except IntegrityError as error:
        await savepoint.rollback()
        return str(getattr(error.orig, "constraint_name", None) or error.orig)
    await savepoint.rollback()
    raise AssertionError("se esperaba una violación de restricción")


async def module(conn: AsyncConnection, code: str = "LC") -> None:
    await conn.execute(
        text(
            """INSERT INTO content.modules (code, name, question_type, options_per_item,
                   max_context_words, exam_questions, bank_target, position)
               VALUES (:c, 'Lectura crítica', 'selection', 4, 500, 30, 150, 1)"""
        ),
        {"c": code},
    )


async def item(conn: AsyncConnection, code: str = "LC-0001") -> Any:
    return await scalar(
        conn,
        """INSERT INTO content.items (code, module_code, kind, origin)
           VALUES (:c, 'LC', 'selection', 'teacher') RETURNING id""",
        c=code,
    )


VERSION = """INSERT INTO content.item_versions
    (item_id, number, state, difficulty, stem_md, explanation_md, content_hash, fingerprint,
     contributor_ids, retire_reason)
    VALUES (:item, :n, :state, :difficulty, 'Enunciado', 'Explicación', '\\x01', '\\x02',
            '{}', :reason)"""


async def test_existen_las_tablas_del_modelo(conn: AsyncConnection) -> None:
    rows = await conn.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'content'")
    )

    assert {row[0] for row in rows} == TABLES


async def test_una_sola_version_publicada_y_una_abierta_por_item(conn: AsyncConnection) -> None:
    await module(conn)
    item_id = await item(conn)
    base = {"item": item_id, "difficulty": "low", "reason": None}
    await conn.execute(text(VERSION), {**base, "n": 1, "state": "published"})
    await conn.execute(text(VERSION), {**base, "n": 2, "state": "draft"})

    assert "ux_item_versions_one_published" in await violates(
        conn, VERSION, **base, n=3, state="published"
    )
    assert "ux_item_versions_one_open" in await violates(
        conn, VERSION, **base, n=4, state="in_review"
    )
    assert "uq_item_versions_number" in await violates(
        conn, VERSION, **{**base, "reason": "Rechazado"}, n=1, state="retired"
    )


@pytest.mark.parametrize(
    ("column", "value", "constraint"),
    [
        ("state", "approved", "ck_item_versions_state"),
        ("difficulty", "easy", "ck_item_versions_difficulty"),
    ],
)
async def test_valores_permitidos_de_las_versiones(
    conn: AsyncConnection, column: str, value: str, constraint: str
) -> None:
    await module(conn)
    item_id = await item(conn)
    params = {"item": item_id, "n": 1, "state": "draft", "difficulty": "low", "reason": None}
    params[column] = value

    assert constraint in await violates(conn, VERSION, **params)


async def test_una_version_retirada_exige_motivo(conn: AsyncConnection) -> None:
    await module(conn)
    item_id = await item(conn)

    assert "ck_item_versions_retire_reason" in await violates(
        conn, VERSION, item=item_id, n=1, state="retired", difficulty="low", reason=None
    )


@pytest.mark.parametrize(
    ("sql", "constraint"),
    [
        (
            "INSERT INTO content.items (code, module_code, kind, origin)"
            " VALUES ('LC-9', 'LC', 'essay', 'teacher')",
            "ck_items_kind",
        ),
        (
            "INSERT INTO content.items (code, module_code, kind, origin)"
            " VALUES ('LC-9', 'LC', 'selection', 'web')",
            "ck_items_origin",
        ),
        (
            "INSERT INTO content.media (sha256, content_type, width, height, size_bytes, data,"
            " created_by) VALUES ('\\x01', 'image/svg+xml', 1, 1, 1, '\\x00', uuidv7())",
            "ck_media_content_type",
        ),
        (
            "INSERT INTO content.media (sha256, content_type, width, height, size_bytes, data,"
            " created_by) VALUES ('\\x02', 'image/png', 1, 1, 1048577, '\\x00', uuidv7())",
            "ck_media_size_bytes",
        ),
    ],
)
async def test_restricciones_de_items_e_imagenes(
    conn: AsyncConnection, sql: str, constraint: str
) -> None:
    await module(conn)

    assert constraint in await violates(conn, sql)


CONTEXT_VERSION = """INSERT INTO content.context_versions
    (context_id, number, kind, title, body_md, alt_text, word_count, origin, content_hash)
    VALUES (:ctx, :n, :kind, 'Título', 'Texto', :alt, :words, 'teacher', '\\x01')"""


async def test_contextos_limite_de_palabras_y_texto_alternativo(conn: AsyncConnection) -> None:
    await module(conn)
    ctx = await scalar(
        conn,
        "INSERT INTO content.contexts (code, module_code) VALUES ('LC-CTX-1', 'LC') RETURNING id",
    )
    await conn.execute(
        text(CONTEXT_VERSION), {"ctx": ctx, "n": 1, "kind": "text", "alt": None, "words": 500}
    )

    assert "ck_context_versions_word_count" in await violates(
        conn, CONTEXT_VERSION, ctx=ctx, n=2, kind="text", alt=None, words=501
    )
    assert "ck_context_versions_alt_text" in await violates(
        conn, CONTEXT_VERSION, ctx=ctx, n=3, kind="image", alt="  ", words=None
    )
    assert "ck_context_versions_kind" in await violates(
        conn, CONTEXT_VERSION, ctx=ctx, n=4, kind="video", alt=None, words=None
    )


async def test_codigos_de_taxonomia_unicos(conn: AsyncConnection) -> None:
    await module(conn)
    insert = """INSERT INTO content.taxonomy_nodes (module_code, kind, code, name, position)
                VALUES ('LC', :kind, 'LC-A1', 'Afirmación', 1)"""
    await conn.execute(text(insert), {"kind": "assertion"})

    assert "uq_taxonomy_nodes_code" in await violates(conn, insert, kind="assertion")
    assert "ck_taxonomy_nodes_kind" in await violates(
        conn, insert.replace("LC-A1", "LC-X1"), kind="topic"
    )


async def test_busqueda_de_texto_completo_en_espanol(conn: AsyncConnection) -> None:
    await module(conn)
    item_id = await item(conn)
    await conn.execute(
        text(VERSION.replace("'Enunciado'", "'Los estudiantes leyeron columnas de opinión'")),
        {"item": item_id, "n": 1, "state": "draft", "difficulty": "low", "reason": None},
    )

    # La configuración `spanish` reduce "leyeron" y "columnas" a su raíz.
    found = await scalar(
        conn,
        """SELECT count(*) FROM content.item_versions
           WHERE search @@ plainto_tsquery('spanish', 'columna estudiante')""",
    )
    index = await scalar(
        conn,
        """SELECT indexdef FROM pg_indexes
           WHERE schemaname = 'content' AND indexname = 'ix_item_versions_search'""",
    )

    assert found == 1
    assert "gin" in index.lower()
