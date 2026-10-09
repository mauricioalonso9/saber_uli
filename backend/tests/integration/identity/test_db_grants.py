"""T029: permisos de base de datos por rol (FR-035; research R-07; data-model §2.10, §2.11, §2.14).

La base de datos, no solo el código, garantiza que la auditoría y los consentimientos sean de
solo inserción y que las versiones de la política sean inmutables para `saber_app`.
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

APPEND_ONLY = ("identity.audit_events", "identity.consents")


async def connect(url: str) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def app(migrated_database: dict[str, str]) -> AsyncIterator[AsyncConnection]:
    async for connection in connect(migrated_database["app"]):
        yield connection


@pytest.fixture
async def bi(migrated_database: dict[str, str]) -> AsyncIterator[AsyncConnection]:
    async for connection in connect(migrated_database["bi"]):
        yield connection


async def run(conn: AsyncConnection, sql: str, **params: Any) -> Any:
    return await conn.execute(text(sql), params)


async def denied(conn: AsyncConnection, sql: str, **params: Any) -> None:
    with pytest.raises(DBAPIError, match=r"permission denied|must be owner"):
        async with conn.begin_nested():
            await run(conn, sql, **params)


@pytest.fixture
async def records(app: AsyncConnection) -> dict[str, UUID]:
    """Usuario, versión de política, consentimiento y evento de auditoría creados por saber_app."""
    user = (
        await run(
            app,
            """INSERT INTO identity.users (kind, email, display_name)
               VALUES ('guest', 'invitado@correo.co', 'Invitado') RETURNING id""",
        )
    ).scalar_one()
    policy = (
        await run(
            app,
            """INSERT INTO identity.policy_versions (version, title, body_markdown, effective_from)
               VALUES ('9.9', 'Política', '...', now()) RETURNING id""",
        )
    ).scalar_one()
    consent = (
        await run(
            app,
            """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
               VALUES (:u, :p, 'accepted', 'web_pwa') RETURNING id""",
            u=user,
            p=policy,
        )
    ).scalar_one()
    audit = (
        await run(
            app,
            """INSERT INTO identity.audit_events (action, target_type, target_id, details)
               VALUES ('user.created', 'user', :u, '{}') RETURNING id""",
            u=user,
        )
    ).scalar_one()
    return {"user": user, "policy": policy, "consent": consent, "audit": audit}


# --- saber_app: DML donde corresponde ----------------------------------------------------------


async def test_saber_app_inserta_y_lee_en_las_tablas_de_solo_insercion(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    consents = await run(
        app, "SELECT count(*) FROM identity.consents WHERE id = :id", id=records["consent"]
    )
    audits = await run(
        app, "SELECT count(*) FROM identity.audit_events WHERE id = :id", id=records["audit"]
    )

    assert consents.scalar_one() == 1
    assert audits.scalar_one() == 1


@pytest.mark.parametrize("table", APPEND_ONLY)
async def test_saber_app_no_modifica_ni_borra_auditoria_ni_consentimientos(
    app: AsyncConnection, records: dict[str, UUID], table: str
) -> None:
    key = "audit" if table.endswith("audit_events") else "consent"
    column = "details = '{}'" if key == "audit" else "channel = 'otro'"

    await denied(app, f"UPDATE {table} SET {column} WHERE id = :id", id=records[key])  # noqa: S608
    await denied(app, f"DELETE FROM {table} WHERE id = :id", id=records[key])  # noqa: S608
    await denied(app, f"TRUNCATE {table}")


async def test_las_versiones_de_politica_son_inmutables(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await denied(
        app,
        "UPDATE identity.policy_versions SET title = 'otro' WHERE id = :id",
        id=records["policy"],
    )
    await denied(app, "DELETE FROM identity.policy_versions WHERE id = :id", id=records["policy"])


async def test_las_lapidas_no_se_borran(app: AsyncConnection, records: dict[str, UUID]) -> None:
    # La supresión deja una lápida (FR-033); nunca se borra la fila del usuario.
    await denied(app, "DELETE FROM identity.users WHERE id = :id", id=records["user"])
    await run(
        app,
        "UPDATE identity.users SET display_name = 'Nuevo nombre' WHERE id = :id",
        id=records["user"],
    )


async def test_saber_app_tiene_dml_en_las_demas_tablas(
    app: AsyncConnection, records: dict[str, UUID]
) -> None:
    await run(
        app,
        "INSERT INTO identity.role_assignments (user_id, role) VALUES (:u, 'guest')",
        u=records["user"],
    )
    await run(app, "DELETE FROM identity.role_assignments WHERE user_id = :u", u=records["user"])
    await run(
        app,
        """INSERT INTO identity.settings (key, value) VALUES ('prueba_grants', '1')
           ON CONFLICT (key) DO UPDATE SET value = '2'""",
    )
    await run(
        app,
        """INSERT INTO shared.outbox_events (context, event_type, payload, occurred_at)
           VALUES ('identity', 'identity.UserErased', '{}', now())""",
    )
    await run(app, "UPDATE shared.outbox_events SET attempts = attempts + 1")


async def test_saber_app_no_ejecuta_ddl(app: AsyncConnection) -> None:
    await denied(app, "CREATE TABLE identity.x (id int)")
    await denied(app, "CREATE TABLE shared.x (id int)")
    await denied(app, "ALTER TABLE identity.users ADD COLUMN x int")
    await denied(app, "DROP TABLE identity.settings")
    await denied(app, "CREATE SCHEMA otra")


async def test_saber_app_no_toca_la_version_de_alembic(app: AsyncConnection) -> None:
    await denied(app, "UPDATE shared.alembic_version SET version_num = 'x'")


# --- saber_bi: sin acceso a identity ni shared -------------------------------------------------


@pytest.mark.parametrize(
    "table", ["identity.users", "identity.audit_events", "shared.outbox_events"]
)
async def test_saber_bi_no_lee_identity_ni_shared(bi: AsyncConnection, table: str) -> None:
    await denied(bi, f"SELECT 1 FROM {table} LIMIT 1")  # noqa: S608


# --- Privilegios por defecto para tablas futuras ----------------------------------------------


async def test_las_tablas_nuevas_heredan_los_permisos(migrated_database: dict[str, str]) -> None:
    async for migrator in connect(migrated_database["migrator"]):
        await run(migrator, "CREATE TABLE identity.futura (id int PRIMARY KEY)")
        rows = await run(
            migrator,
            """SELECT privilege_type FROM information_schema.role_table_grants
               WHERE grantee = 'saber_app' AND table_schema = 'identity'
                 AND table_name = 'futura'""",
        )
        assert set(rows.scalars()) == {"SELECT", "INSERT", "UPDATE", "DELETE"}
