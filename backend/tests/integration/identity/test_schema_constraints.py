"""T027: restricciones del esquema `identity` (data-model.md §2) y del outbox (§3.1).

Corre con el rol `saber_migrator` (dueño de las tablas): los permisos de `saber_app` llegan con
la migración 0003 (T030). Cada prueba trabaja en una transacción que se revierte; cada violación
se prueba dentro de un savepoint.
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

TENANT = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
async def conn(migrated_database: dict[str, str]) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


async def run(conn: AsyncConnection, sql: str, **params: Any) -> Any:
    return await conn.execute(text(sql), params)


async def violates(conn: AsyncConnection, sql: str, **params: Any) -> None:
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await run(conn, sql, **params)


async def institutional(
    conn: AsyncConnection, oid: str, email: str = "ana@unilibre.edu.co"
) -> UUID:
    result = await run(
        conn,
        """INSERT INTO identity.users (kind, entra_tenant_id, entra_object_id, email, display_name)
           VALUES ('institutional', :tid, :oid, :email, 'Ana') RETURNING id""",
        tid=TENANT,
        oid=oid,
        email=email,
    )
    return UUID(str(result.scalar_one()))


async def guest(conn: AsyncConnection, email: str, status: str = "active") -> UUID:
    result = await run(
        conn,
        """INSERT INTO identity.users (kind, status, email, display_name)
           VALUES ('guest', :status, :email, 'Invitado') RETURNING id""",
        status=status,
        email=email,
    )
    return UUID(str(result.scalar_one()))


OID_1 = "aaaaaaaa-0000-4000-8000-000000000001"
OID_2 = "aaaaaaaa-0000-4000-8000-000000000002"


# --- users (§2.1) ----------------------------------------------------------------------------


async def test_claves_uuidv7_y_valores_por_defecto(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)
    row = (
        await run(
            conn,
            """SELECT uuid_extract_version(id), status, auth_epoch, created_at IS NOT NULL
               FROM identity.users WHERE id = :id""",
            id=user_id,
        )
    ).one()

    assert tuple(row) == (7, "active", 0, True)


@pytest.mark.parametrize(("column", "value"), [("kind", "staff"), ("status", "blocked")])
async def test_kind_y_status_validos(conn: AsyncConnection, column: str, value: str) -> None:
    kind = value if column == "kind" else "guest"
    status = value if column == "status" else "active"
    await violates(
        conn,
        "INSERT INTO identity.users (kind, status, email) VALUES (:kind, :status, 'x@y.co')",
        kind=kind,
        status=status,
    )


async def test_una_cuenta_por_identidad_institucional(conn: AsyncConnection) -> None:
    await institutional(conn, OID_1)

    await violates(
        conn,
        """INSERT INTO identity.users (kind, entra_tenant_id, entra_object_id, email)
           VALUES ('institutional', :tid, :oid, 'otra@unilibre.edu.co')""",
        tid=TENANT,
        oid=OID_1,
    )


async def test_institucional_activo_exige_tid_y_oid(conn: AsyncConnection) -> None:
    await violates(
        conn,
        "INSERT INTO identity.users (kind, email) VALUES ('institutional', 'x@unilibre.edu.co')",
    )


async def test_la_lapida_no_tiene_datos_personales(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)

    await violates(conn, "UPDATE identity.users SET status = 'deleted' WHERE id = :id", id=user_id)
    await run(
        conn,
        """UPDATE identity.users
           SET status = 'deleted', email = NULL, display_name = NULL, entra_object_id = NULL
           WHERE id = :id""",
        id=user_id,
    )


async def test_un_invitado_vigente_por_correo(conn: AsyncConnection) -> None:
    await guest(conn, "Invitado@Correo.co")

    await violates(
        conn,
        "INSERT INTO identity.users (kind, email) VALUES ('guest', 'invitado@correo.CO')",
    )
    # Una lápida no bloquea el correo; tampoco un institucional con el mismo correo.
    await run(
        conn,
        "INSERT INTO identity.users (kind, status) VALUES ('guest', 'deleted')",
    )


async def test_el_correo_no_distingue_mayusculas(conn: AsyncConnection) -> None:
    await guest(conn, "Mixto@Correo.co")
    found = await run(conn, "SELECT count(*) FROM identity.users WHERE email = 'mixto@correo.co'")

    assert found.scalar_one() == 1


# --- profiles (§2.2) ---------------------------------------------------------------------------


@pytest.mark.parametrize("semester", [0, 13])
async def test_semestre_entre_1_y_12(conn: AsyncConnection, semester: int) -> None:
    user_id = await institutional(conn, OID_1)

    await violates(
        conn,
        "INSERT INTO identity.profiles (user_id, semester) VALUES (:id, :s)",
        id=user_id,
        s=semester,
    )


async def test_meta_diaria_valida(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)

    await violates(
        conn,
        "INSERT INTO identity.profiles (user_id, daily_goal) VALUES (:id, 'extremo')",
        id=user_id,
    )
    await run(
        conn,
        "INSERT INTO identity.profiles (user_id, semester, daily_goal) VALUES (:id, 5, 'regular')",
        id=user_id,
    )


# --- role_assignments (§2.3) ---------------------------------------------------------------------


async def test_roles_validos_y_sin_duplicados(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)
    sql = "INSERT INTO identity.role_assignments (user_id, role) VALUES (:id, :role)"

    await run(conn, sql, id=user_id, role="student")
    await violates(conn, sql, id=user_id, role="student")
    await violates(conn, sql, id=user_id, role="superuser")
    for role in ("teacher", "program_director", "admin"):
        await run(conn, sql, id=user_id, role=role)


# --- invitations y access_links (§2.7, §2.8) ------------------------------------------------------


async def invitation(
    conn: AsyncConnection, inviter: UUID, email: str, status: str = "sent"
) -> UUID:
    result = await run(
        conn,
        """INSERT INTO identity.invitations (email, invited_by, status, access_expires_at)
           VALUES (:email, :by, :status, now() + interval '90 days') RETURNING id""",
        email=email,
        by=inviter,
        status=status,
    )
    return UUID(str(result.scalar_one()))


async def test_estado_de_invitacion_valido(conn: AsyncConnection) -> None:
    inviter = await institutional(conn, OID_1)

    await violates(
        conn,
        """INSERT INTO identity.invitations (email, invited_by, status, access_expires_at)
           VALUES ('x@y.co', :by, 'pending', now() + interval '1 day')""",
        by=inviter,
    )


async def test_una_invitacion_vigente_por_correo(conn: AsyncConnection) -> None:
    inviter = await institutional(conn, OID_1)
    await invitation(conn, inviter, "Uno@Correo.co", "sent")

    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await invitation(conn, inviter, "uno@correo.co", "accepted")
    # Las vencidas o revocadas no cuentan.
    await invitation(conn, inviter, "dos@correo.co", "revoked")
    await invitation(conn, inviter, "dos@correo.co", "expired")
    await invitation(conn, inviter, "dos@correo.co", "sent")


async def test_el_acceso_vence_despues_de_crearse(conn: AsyncConnection) -> None:
    inviter = await institutional(conn, OID_1)

    await violates(
        conn,
        """INSERT INTO identity.invitations (email, invited_by, status, access_expires_at)
           VALUES ('x@y.co', :by, 'sent', now() - interval '1 day')""",
        by=inviter,
    )


async def test_enlaces_proposito_valido_y_hash_unico(conn: AsyncConnection) -> None:
    inviter = await institutional(conn, OID_1)
    inv = await invitation(conn, inviter, "x@y.co")
    sql = """INSERT INTO identity.access_links (invitation_id, purpose, token_hash, expires_at)
             VALUES (:inv, :purpose, :hash, now() + interval '15 minutes')"""
    token_hash = bytes(range(32))

    await violates(conn, sql, inv=inv, purpose="reset", hash=token_hash)
    await run(conn, sql, inv=inv, purpose="sign_in", hash=token_hash)
    await violates(conn, sql, inv=inv, purpose="invitation", hash=token_hash)
    # Solo hashes SHA-256 (32 bytes): nunca un token en claro.
    await violates(conn, sql, inv=inv, purpose="invitation", hash=b"token-en-claro")


# --- consents y deletion_requests (§2.11, §2.12) -------------------------------------------------


async def policy(conn: AsyncConnection) -> UUID:
    result = await run(
        conn,
        """INSERT INTO identity.policy_versions (version, title, body_markdown, effective_from)
           VALUES ('1.0', 'Política', '...', now()) RETURNING id""",
    )
    return UUID(str(result.scalar_one()))


async def test_decision_de_consentimiento_valida(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)
    version = await policy(conn)
    sql = """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
             VALUES (:u, :p, :d, 'web_pwa')"""

    await violates(conn, sql, u=user_id, p=version, d="maybe")
    for decision in ("accepted", "rejected", "revoked"):
        await run(conn, sql, u=user_id, p=version, d=decision)


async def test_version_de_politica_unica(conn: AsyncConnection) -> None:
    await policy(conn)

    await violates(
        conn,
        """INSERT INTO identity.policy_versions (version, title, body_markdown, effective_from)
           VALUES ('1.0', 'Otra', '...', now())""",
    )


@pytest.mark.parametrize(("column", "value"), [("origin", "admin"), ("status", "cancelled")])
async def test_solicitud_de_supresion_valores_validos(
    conn: AsyncConnection, column: str, value: str
) -> None:
    user_id = await institutional(conn, OID_1)
    origin = value if column == "origin" else "user_request"
    status = value if column == "status" else "received"

    await violates(
        conn,
        """INSERT INTO identity.deletion_requests (user_id, origin, status, due_date)
           VALUES (:u, :o, :s, current_date + 21)""",
        u=user_id,
        o=origin,
        s=status,
    )


async def test_una_solicitud_abierta_por_usuario(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)
    sql = """INSERT INTO identity.deletion_requests (user_id, origin, status, due_date)
             VALUES (:u, 'user_request', :s, current_date + 21)"""

    await run(conn, sql, u=user_id, s="completed")
    await run(conn, sql, u=user_id, s="received")
    await violates(conn, sql, u=user_id, s="in_progress")


# --- sesiones, auditoría, parámetros y outbox (§2.13 a §2.15, §3.1) ------------------------------


async def test_sesiones_y_tokens_de_renovacion(conn: AsyncConnection) -> None:
    user_id = await institutional(conn, OID_1)
    sql = """INSERT INTO identity.sessions (user_id, auth_method, auth_time, last_seen_at,
                 absolute_expires_at)
             VALUES (:u, :m, now(), now(), now() + interval '30 days') RETURNING id"""

    await violates(conn, sql, u=user_id, m="password")
    session_id = (await run(conn, sql, u=user_id, m="entra_id")).scalar_one()
    token_sql = """INSERT INTO identity.refresh_tokens (session_id, token_hash, idle_expires_at)
                   VALUES (:s, :h, now() + interval '7 days')"""
    await run(conn, token_sql, s=session_id, h=bytes(32))
    await violates(conn, token_sql, s=session_id, h=bytes(32))


async def test_auditoria_tipo_de_objeto_valido(conn: AsyncConnection) -> None:
    sql = """INSERT INTO identity.audit_events (action, target_type, details)
             VALUES ('user.created', :t, '{}')"""

    await violates(conn, sql, t="planeta")
    await run(conn, sql, t="user")


async def test_tablas_restantes_existen(conn: AsyncConnection) -> None:
    rows = await run(
        conn,
        """SELECT table_schema || '.' || table_name FROM information_schema.tables
           WHERE table_schema IN ('identity', 'shared')""",
    )
    tables = set(rows.scalars())

    assert {
        "identity.users",
        "identity.profiles",
        "identity.role_assignments",
        "identity.director_programs",
        "identity.programs",
        "identity.groups",
        "identity.group_members",
        "identity.group_teachers",
        "identity.invitations",
        "identity.access_links",
        "identity.invitation_batches",
        "identity.policy_versions",
        "identity.consents",
        "identity.deletion_requests",
        "identity.sessions",
        "identity.refresh_tokens",
        "identity.audit_events",
        "identity.settings",
        "shared.outbox_events",
        "shared.alembic_version",
    } <= tables


async def test_outbox_indice_parcial_de_pendientes(conn: AsyncConnection) -> None:
    rows = await run(
        conn,
        """SELECT indexdef FROM pg_indexes
           WHERE schemaname = 'shared' AND tablename = 'outbox_events'""",
    )
    definitions = " ".join(rows.scalars())

    assert "(available_at)" in definitions
    assert "WHERE (processed_at IS NULL)" in definitions


async def test_outbox_valores_por_defecto(conn: AsyncConnection) -> None:
    result = await run(
        conn,
        """INSERT INTO shared.outbox_events (context, event_type, payload, occurred_at)
           VALUES ('identity', 'identity.UserErased', '{}', now())
           RETURNING uuid_extract_version(id), attempts, available_at IS NOT NULL,
                     processed_at IS NULL""",
    )

    assert tuple(result.one()) == (7, 0, True, True)


async def test_el_outbox_rechaza_payload_que_no_es_objeto(conn: AsyncConnection) -> None:
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await run(
                conn,
                """INSERT INTO shared.outbox_events (context, event_type, payload, occurred_at)
                   VALUES ('identity', 'identity.UserErased', '[1, 2]', now())""",
            )
