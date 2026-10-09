"""T155: borrado de los datos personales (FR-033; escenarios 7.2 y 7.3; research R-25).

- La fila del usuario queda como lápida: `status = 'deleted'` y sin nombre, correo ni `oid`.
- Se borran perfil, roles, programas del director, membresías de grupos, sesiones y, de sus
  invitaciones como invitado, el correo, el nombre y los enlaces.
- Se conservan las autorizaciones (`consents`) y la auditoría, enlazadas solo al UUID.
- El contenido que creó (invitaciones que envió, grupos) se conserva sin datos personales.
- Se publica `identity.UserErased`; la solicitud queda `completed` y se audita.
- Es idempotente: si el proceso se reanuda desde `in_progress`, completa lo que falta.
- Tras el borrado, el mismo `oid` crea una cuenta nueva sin historial.
- Revisión automática: ninguna fila del esquema `identity` ni del outbox contiene el correo, el
  nombre o el `oid` borrados.
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from saber_uli.identity.application.deletion import DeletionService
from saber_uli.identity.application.erase_user import EraseUser
from saber_uli.identity.domain.events import UserErased
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import User
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from saber_uli.shared.infrastructure.outbox import register_outbox
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.catalog import ProgramFactory
from tests.integration.identity.guests import Guests
from tests.integration.identity.staff import accept_current_policy


@pytest.fixture
def uow_factory(app_engine: AsyncEngine) -> Any:
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    register_outbox(bus, UserErased, context="identity")
    return lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus)


@pytest.fixture
def deletion(uow_factory: Any) -> DeletionService:
    return DeletionService(uow_factory=uow_factory, clock=SystemClock())


@pytest.fixture
def erase(uow_factory: Any) -> EraseUser:
    return EraseUser(uow_factory=uow_factory, clock=SystemClock())


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement), params)


async def scalar(engine: AsyncEngine, statement: str, **params: Any) -> Any:
    """Un valor; confirma, así sirve también para `INSERT … RETURNING`."""
    async with engine.begin() as conn:
        return (await conn.execute(text(statement), params)).scalar_one()


async def count(engine: AsyncEngine, table: str, user_id: UUID) -> int:
    value: int = await scalar(
        engine,
        f"SELECT count(*) FROM identity.{table} WHERE user_id = :u",  # noqa: S608
        u=user_id,
    )
    return value


async def audit_actions(engine: AsyncEngine, user_id: UUID) -> list[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT action FROM identity.audit_events
                   WHERE subject_user_id = :u ORDER BY occurred_at, id"""
            ),
            {"u": user_id},
        )
        return list(rows.scalars())


async def rows_containing(engine: AsyncEngine, needle: str) -> list[str]:
    """Tablas de `identity` (y el outbox) con alguna fila cuyo texto contiene `needle`."""
    async with engine.connect() as conn:
        tables = list(
            (
                await conn.execute(
                    text(
                        """SELECT table_schema || '.' || table_name
                           FROM information_schema.tables
                           WHERE table_type = 'BASE TABLE'
                             AND (table_schema = 'identity'
                                  OR (table_schema, table_name) = ('shared', 'outbox_events'))"""
                    )
                )
            ).scalars()
        )
        found = []
        for table in tables:
            hits = (
                await conn.execute(
                    text(f"SELECT count(*) FROM {table} AS r WHERE r::text ILIKE :p"),  # noqa: S608
                    {"p": f"%{needle}%"},
                )
            ).scalar_one()
            if hits:
                found.append(table)
        return found


async def test_deja_una_lapida_sin_datos_personales(
    committed_login: CommittedLogin,
    new_program: ProgramFactory,
    deletion: DeletionService,
    erase: EraseUser,
    app_engine: AsyncEngine,
    migrated_database: dict[str, str],
) -> None:
    owner, _ = await committed_login(Role.ADMIN)
    user, _ = await committed_login(Role.TEACHER)
    assert user.id is not None and owner.id is not None and user.entra_identity is not None
    name = f"Nombre Borrable {uuid4().hex[:8]}"
    await sql(
        app_engine, "UPDATE identity.users SET display_name = :n WHERE id = :u", n=name, u=user.id
    )
    program = await new_program()
    await sql(
        app_engine,
        "INSERT INTO identity.director_programs (user_id, program_id) VALUES (:u, :p)",
        u=user.id,
        p=program,
    )
    await sql(
        app_engine,
        "INSERT INTO identity.role_assignments (user_id, role) VALUES (:u, 'program_director')",
        u=user.id,
    )
    await sql(
        app_engine,
        """INSERT INTO identity.profiles (user_id, program_id, semester, daily_goal)
           VALUES (:u, :p, 5, 'regular')""",
        u=user.id,
        p=program,
    )
    group = await scalar(
        app_engine,
        "INSERT INTO identity.groups (name, created_by) VALUES ('Grupo T155', :o) RETURNING id",
        o=owner.id,
    )
    own_group = await scalar(
        app_engine,
        "INSERT INTO identity.groups (name, created_by) VALUES ('Suyo T155', :u) RETURNING id",
        u=user.id,
    )
    for table in ("group_members", "group_teachers"):
        await sql(
            app_engine,
            f"INSERT INTO identity.{table} (group_id, user_id) VALUES (:g, :u)",  # noqa: S608
            g=group,
            u=user.id,
        )
    sent = await scalar(
        app_engine,
        """INSERT INTO identity.invitations (email, invited_by, status, access_expires_at)
           VALUES (:e, :u, 'sent', now() + interval '30 days') RETURNING id""",
        e=f"invitada-{uuid4().hex[:8]}@correo.co",
        u=user.id,
    )
    await accept_current_policy(app_engine, user.id)

    request = await deletion.request(user.id)
    assert request.id is not None
    assert await erase.execute(request.id) is True

    tomb = await scalar(
        app_engine,
        """SELECT row(status, email, display_name, entra_object_id, retention_notice_sent_at)
           FROM identity.users WHERE id = :u""",
        u=user.id,
    )
    assert tomb == ("deleted", None, None, None, None)
    for table in (
        "profiles",
        "role_assignments",
        "director_programs",
        "group_members",
        "group_teachers",
        "sessions",
    ):
        assert await count(app_engine, table, user.id) == 0, table
    # Se conservan como prueba, solo con el UUID.
    assert await count(app_engine, "consents", user.id) == 1
    assert (
        await scalar(app_engine, "SELECT count(*) FROM identity.groups WHERE id = :g", g=own_group)
        == 1
    )
    assert (
        await scalar(
            app_engine, "SELECT invited_by FROM identity.invitations WHERE id = :i", i=sent
        )
        == user.id
    )

    request_row = await scalar(
        app_engine,
        """SELECT row(status, completed_at IS NOT NULL)
           FROM identity.deletion_requests WHERE id = :r""",
        r=request.id,
    )
    assert request_row == ("completed", True)
    assert (await audit_actions(app_engine, user.id))[-3:] == [
        "deletion.requested",
        "user.erased",
        "deletion.completed",
    ]
    assert (
        await scalar(
            app_engine,
            """SELECT count(*) FROM shared.outbox_events
           WHERE event_type = 'identity.UserErased' AND payload->>'user_id' = :u""",
            u=str(user.id),
        )
        == 1
    )

    # Revisión automática (FR-033): nada en `identity` ni en el outbox identifica a la persona.
    assert user.email is not None
    migrator = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    try:
        for needle in (user.email, name, str(user.entra_identity.object_id)):
            assert await rows_containing(migrator, needle) == [], needle
    finally:
        await migrator.dispose()


async def test_es_idempotente_y_se_reanuda(
    committed_login: CommittedLogin,
    deletion: DeletionService,
    erase: EraseUser,
    app_engine: AsyncEngine,
) -> None:
    user, _ = await committed_login()
    assert user.id is not None
    request = await deletion.request(user.id)
    assert request.id is not None
    # El worker cayó después de marcarla en proceso.
    await sql(
        app_engine,
        "UPDATE identity.deletion_requests SET status = 'in_progress' WHERE id = :r",
        r=request.id,
    )

    assert await erase.execute(request.id) is True
    assert await erase.execute(request.id) is False  # ya estaba completa

    assert (
        await scalar(app_engine, "SELECT status FROM identity.users WHERE id = :u", u=user.id)
        == "deleted"
    )
    assert (
        await scalar(
            app_engine,
            """SELECT count(*) FROM identity.audit_events
           WHERE subject_user_id = :u AND action = 'deletion.completed'""",
            u=user.id,
        )
        == 1
    )


async def test_borra_el_contacto_de_sus_invitaciones_como_invitado(
    committed_login: CommittedLogin,
    guests: Guests,
    deletion: DeletionService,
    erase: EraseUser,
    app_engine: AsyncEngine,
) -> None:
    teacher, _ = await committed_login(Role.TEACHER)
    guest, _ = await committed_login(guest=True)
    assert guest.id is not None and teacher.id is not None
    invitation_id, _ = await guests.invitation(
        teacher.id, email=guest.email, status="accepted", guest_user_id=guest.id
    )
    await sql(
        app_engine,
        "UPDATE identity.invitations SET invitee_name = 'Invitada T155' WHERE id = :i",
        i=invitation_id,
    )
    await guests.link(invitation_id, purpose="sign_in")

    request = await deletion.request(guest.id)
    assert request.id is not None
    await erase.execute(request.id)

    invitation = await scalar(
        app_engine,
        "SELECT row(status, email, invitee_name) FROM identity.invitations WHERE id = :i",
        i=invitation_id,
    )
    assert invitation == ("accepted", None, None)
    assert (
        await scalar(
            app_engine,
            "SELECT count(*) FROM identity.access_links WHERE invitation_id = :i",
            i=invitation_id,
        )
        == 0
    )


async def test_reingresar_con_el_mismo_oid_crea_una_cuenta_nueva(
    committed_login: CommittedLogin,
    deletion: DeletionService,
    erase: EraseUser,
    db_session: AsyncSession,
) -> None:
    user, _ = await committed_login()
    assert user.id is not None and user.entra_identity is not None and user.email is not None
    request = await deletion.request(user.id)
    assert request.id is not None
    await erase.execute(request.id)

    users = SqlAlchemyUserRepository(db_session)
    assert await users.get_by_entra_identity(user.entra_identity) is None
    again = await users.add(
        User.new_institutional(
            user.entra_identity, email=user.email, display_name="Persona", now=user.created_at
        )
    )
    assert again.id is not None and again.id != user.id
    assert again.roles == {Role.STUDENT}
    assert again.onboarding_completed_at is None
