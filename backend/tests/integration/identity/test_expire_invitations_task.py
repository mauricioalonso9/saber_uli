"""T126: tarea `expire_invitations` (data-model §4.2; FR-011, FR-034e).

- `sent` cuyo enlace o acceso venció → `expired`.
- `accepted` con el acceso vencido → `expired` y `auth_epoch` + 1 del invitado (sus sesiones
  terminan en la siguiente petición).
- Idempotente.
- Una invitación nunca aceptada pierde correo, nombre y enlaces 90 días después de su revocación
  o, si no fue revocada, del vencimiento de su enlace (`invitation.contact_purged`).
- `last_delivery_status` refleja el resultado del manejador de correo.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.handlers.link_emails import LinkEmailHandlers
from saber_uli.identity.infrastructure.link_tokens import LinkTokenFactory
from saber_uli.identity.infrastructure.tasks import expire_invitations
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.notifications.application.ports import OutgoingEmail
from saber_uli.notifications.application.public import EmailService
from saber_uli.notifications.infrastructure.templates import JinjaTemplateRenderer
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from saber_uli.shared.infrastructure.outbox import OutboxMessage
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.guests import Guests


@pytest.fixture
async def teacher(committed_login: CommittedLogin) -> UUID:
    user, _ = await committed_login(Role.TEACHER)
    assert user.id is not None
    return user.id


@pytest.fixture
def uow_factory(app_engine: AsyncEngine) -> Any:
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    return lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus)


async def run(uow_factory: Any) -> None:
    await expire_invitations(uow_factory=uow_factory, clock=SystemClock())


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement), params)


async def invitation(engine: AsyncEngine, invitation_id: UUID) -> Any:
    async with engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    "SELECT status, email, invitee_name, last_delivery_status"
                    " FROM identity.invitations WHERE id = :id"
                ),
                {"id": invitation_id},
            )
        ).one()


async def epoch(engine: AsyncEngine, user_id: UUID) -> int:
    async with engine.connect() as conn:
        value: int = (
            await conn.execute(
                text("SELECT auth_epoch FROM identity.users WHERE id = :u"), {"u": user_id}
            )
        ).scalar_one()
    return value


async def test_una_invitacion_enviada_con_el_enlace_vencido_pasa_a_expired(
    uow_factory: Any, guests: Guests, teacher: UUID
) -> None:
    link_expired, _ = await guests.invitation(teacher)
    access_expired, _ = await guests.invitation(teacher, access_days=-1)
    still_valid, _ = await guests.invitation(teacher)
    await sql(
        guests.engine,
        "UPDATE identity.invitations SET link_expires_at = now() - interval '1 minute'"
        " WHERE id = :id",
        id=link_expired,
    )

    await run(uow_factory)

    assert (await invitation(guests.engine, link_expired)).status == "expired"
    assert (await invitation(guests.engine, access_expired)).status == "expired"
    assert (await invitation(guests.engine, still_valid)).status == "sent"


async def test_un_acceso_aceptado_que_vencio_termina_las_sesiones_y_es_idempotente(
    uow_factory: Any, guests: Guests, teacher: UUID, api_client: httpx.AsyncClient
) -> None:
    invitation_id, email = await guests.invitation(teacher)
    signed_in = await api_client.post(
        "/api/auth/guest/sessions", json={"token": await guests.link(invitation_id)}
    )
    assert signed_in.status_code == 200
    guest_id = await guests.guest_user_id(email)
    assert guest_id is not None
    before = await epoch(guests.engine, guest_id)
    await sql(
        guests.engine,
        "UPDATE identity.invitations SET access_expires_at = now() - interval '1 second',"
        " created_at = now() - interval '2 days' WHERE id = :id",
        id=invitation_id,
    )

    await run(uow_factory)
    await run(uow_factory)

    assert (await invitation(guests.engine, invitation_id)).status == "expired"
    assert await epoch(guests.engine, guest_id) == before + 1
    headers = {"Authorization": f"Bearer {signed_in.json()['access_token']}"}
    after = await api_client.get("/api/v1/me", headers=headers)
    assert after.status_code == 401
    assert after.json()["type"].endswith("guest-access-expired")


@pytest.mark.parametrize(
    ("case", "purged"),
    [
        ("revocada hace 91 días", True),
        ("revocada hace 89 días", False),
        ("enlace vencido hace 91 días", True),
    ],
)
async def test_purga_del_contacto_de_invitaciones_nunca_aceptadas(
    uow_factory: Any, guests: Guests, teacher: UUID, case: str, purged: bool
) -> None:
    invitation_id, _ = await guests.invitation(teacher)
    await guests.link(invitation_id)
    await sql(
        guests.engine,
        "UPDATE identity.invitations SET invitee_name = 'Laura', created_at = now() - interval"
        " '200 days' WHERE id = :id",
        id=invitation_id,
    )
    if case.startswith("revocada"):
        days = 91 if "91" in case else 89
        await sql(
            guests.engine,
            "UPDATE identity.invitations SET status = 'revoked',"
            " revoked_at = now() - make_interval(days => :d) WHERE id = :id",
            id=invitation_id,
            d=days,
        )
    else:
        await sql(
            guests.engine,
            "UPDATE identity.invitations SET status = 'expired',"
            " link_expires_at = now() - interval '91 days' WHERE id = :id",
            id=invitation_id,
        )

    await run(uow_factory)

    row = await invitation(guests.engine, invitation_id)
    async with guests.engine.connect() as conn:
        links = (
            await conn.execute(
                text("SELECT count(*) FROM identity.access_links WHERE invitation_id = :id"),
                {"id": invitation_id},
            )
        ).scalar_one()
        audited = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM identity.audit_events WHERE target_id = :id"
                    " AND action = 'invitation.contact_purged'"
                ),
                {"id": invitation_id},
            )
        ).scalar_one()
    if purged:
        assert (row.email, row.invitee_name) == (None, None)
        assert (links, audited) == (0, 1)
    else:
        assert row.email is not None and row.invitee_name == "Laura"
        assert (links, audited) == (1, 0)


class FailingSender:
    async def send(self, email: OutgoingEmail) -> None:
        raise ConnectionError("SMTP caído")


async def test_el_estado_de_entrega_refleja_un_fallo_del_correo(
    uow_factory: Any, guests: Guests, teacher: UUID
) -> None:
    invitation_id, _ = await guests.invitation(teacher)
    handlers = LinkEmailHandlers(
        uow_factory=uow_factory,
        email=EmailService(
            renderer=JinjaTemplateRenderer(public_base_url="http://localhost"),
            sender=FailingSender(),
        ),
        clock=SystemClock(),
        tokens=LinkTokenFactory(),
    )
    message = OutboxMessage(
        event_id=uuid4(),
        event_type="identity.InvitationCreated",
        context="identity",
        payload={"invitation_id": str(invitation_id)},
        occurred_at=datetime.now(UTC),
        attempt=1,
    )

    with pytest.raises(ConnectionError):
        await handlers.on_invitation_created(message)

    assert (await invitation(guests.engine, invitation_id)).last_delivery_status == "failed"
