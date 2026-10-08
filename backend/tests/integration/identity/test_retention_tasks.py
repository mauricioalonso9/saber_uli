"""T156: tareas de conservación y supresión (FR-034a a FR-034d, SC-006; research R-09, R-25).

`process_retention` (diaria):

- 30 días antes de la supresión automática encola `identity.RetentionNoticeDue` una sola vez;
  el manejador envía el aviso (Mailpit) con la fecha y cómo evitarla, y audita
  `retention.notice_sent`.
- En la fecha crea la solicitud con origen `institutional_retention` o `guest_retention`.
- Si el correo no se puede enviar, la supresión sigue en la fecha prevista.
- Ingresar antes de la fecha cancela el proceso (el aviso pendiente ya no se envía).
- El último administrador activo no recibe solicitud: se audita `retention.skipped_last_admin`
  una vez por ciclo.

`process_deletion_requests` (cada 15 min) completa las solicitudes y audita
`deletion.completed`.
"""

import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.handlers.link_emails import long_date
from saber_uli.identity.infrastructure.handlers.retention_notice import RetentionNoticeHandler
from saber_uli.identity.infrastructure.outbox_events import register_identity_outbox
from saber_uli.identity.infrastructure.tasks import process_deletion_requests, process_retention
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.notifications.application.ports import OutgoingEmail
from saber_uli.notifications.application.public import EmailService
from saber_uli.notifications.infrastructure.smtp import SmtpEmailSender
from saber_uli.notifications.infrastructure.templates import JinjaTemplateRenderer
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.infrastructure.db import create_session_factory
from saber_uli.shared.infrastructure.outbox import OutboxMessage
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.guests import Guests

BASE_URL = "http://localhost"


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime.now(UTC))


@pytest.fixture
def uow_factory(app_engine: AsyncEngine) -> Any:
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    register_identity_outbox(bus)
    return lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus)


class FailingSender:
    async def send(self, email: OutgoingEmail) -> None:
        raise ConnectionError("SMTP no disponible")


def handler_with(uow_factory: Any, clock: FixedClock, sender: Any) -> RetentionNoticeHandler:
    return RetentionNoticeHandler(
        uow_factory=uow_factory,
        email=EmailService(renderer=JinjaTemplateRenderer(public_base_url=BASE_URL), sender=sender),
        clock=clock,
    )


@pytest.fixture
def handler(
    uow_factory: Any, clock: FixedClock, mailpit: tuple[str, int, str]
) -> RetentionNoticeHandler:
    host, port, _ = mailpit
    sender = SmtpEmailSender(
        host=host, port=port, sender="Saber Uli <no-responder@unilibre.edu.co>", starttls=False
    )
    return handler_with(uow_factory, clock, sender)


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(statement), params)


async def scalar(engine: AsyncEngine, statement: str, **params: Any) -> Any:
    async with engine.connect() as conn:
        return (await conn.execute(text(statement), params)).scalar_one_or_none()


async def last_login(engine: AsyncEngine, user_id: UUID, at: datetime) -> None:
    await sql(engine, "UPDATE identity.users SET last_login_at = :t WHERE id = :u", t=at, u=user_id)


async def notices(engine: AsyncEngine, user_id: UUID) -> list[OutboxMessage]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT id, event_type, context, payload, occurred_at FROM shared.outbox_events
                   WHERE event_type = 'identity.RetentionNoticeDue'
                     AND payload->>'user_id' = :u ORDER BY occurred_at"""
            ),
            {"u": str(user_id)},
        )
        return [
            OutboxMessage(
                event_id=row.id,
                event_type=row.event_type,
                context=row.context,
                payload=row.payload,
                occurred_at=row.occurred_at,
                attempt=1,
            )
            for row in rows
        ]


async def open_request(engine: AsyncEngine, user_id: UUID) -> Any:
    async with engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    """SELECT id, origin, status FROM identity.deletion_requests
                       WHERE user_id = :u ORDER BY requested_at DESC LIMIT 1"""
                ),
                {"u": user_id},
            )
        ).one_or_none()


async def audits(engine: AsyncEngine, user_id: UUID, action: str) -> list[Any]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT actor_id, details FROM identity.audit_events
                   WHERE subject_user_id = :u AND action = :a ORDER BY occurred_at"""
            ),
            {"u": user_id, "a": action},
        )
        return list(rows)


def emails_to(api: str, address: str, count: int = 1, timeout: float = 10) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout
    while True:
        found = httpx.get(
            f"{api}/api/v1/search", params={"query": f'to:"{address}"'}, timeout=5
        ).json()["messages"]
        if len(found) >= count or time.monotonic() > deadline:
            break
        time.sleep(0.2)
    return [httpx.get(f"{api}/api/v1/message/{item['ID']}", timeout=5).json() for item in found]


async def test_aviso_al_institucional_30_dias_antes(
    committed_login: CommittedLogin,
    uow_factory: Any,
    clock: FixedClock,
    handler: RetentionNoticeHandler,
    app_engine: AsyncEngine,
    mailpit: tuple[str, int, str],
) -> None:
    user, _ = await committed_login()
    assert user.id is not None and user.email is not None
    login = clock.now() - timedelta(days=340)
    await last_login(app_engine, user.id, login)

    await process_retention(uow_factory=uow_factory, clock=clock)
    await process_retention(uow_factory=uow_factory, clock=clock)  # no repite el aviso

    (message,) = await notices(app_engine, user.id)
    assert set(message.payload) == {"user_id"}  # solo identificadores (R-19)
    assert (
        await scalar(
            app_engine,
            "SELECT retention_notice_sent_at FROM identity.users WHERE id = :u",
            u=user.id,
        )
        == clock.now()
    )
    assert await open_request(app_engine, user.id) is None

    await handler.on_notice_due(message)

    (mail,) = emails_to(mailpit[2], user.email)
    erase_on = long_date(login + timedelta(days=365))
    for body in (mail["Text"], mail["HTML"]):
        assert erase_on in body
        assert "ingresa" in body.lower()
        assert BASE_URL in body
    (entry,) = await audits(app_engine, user.id, "retention.notice_sent")
    assert entry.actor_id is None
    assert entry.details == {
        "kind": "institutional",
        "erase_on": str((login + timedelta(days=365)).date()),
    }


async def test_aviso_al_invitado_explica_como_pedir_la_renovacion(
    committed_login: CommittedLogin,
    guests: Guests,
    uow_factory: Any,
    clock: FixedClock,
    handler: RetentionNoticeHandler,
    app_engine: AsyncEngine,
    mailpit: tuple[str, int, str],
) -> None:
    teacher, _ = await committed_login(Role.TEACHER)
    guest, _ = await committed_login(guest=True)
    assert guest.id is not None and teacher.id is not None and guest.email is not None
    await guests.invitation(
        teacher.id, email=guest.email, status="expired", guest_user_id=guest.id, access_days=-61
    )

    await process_retention(uow_factory=uow_factory, clock=clock)
    (message,) = await notices(app_engine, guest.id)
    await handler.on_notice_due(message)

    (mail,) = emails_to(mailpit[2], guest.email)
    assert "renov" in mail["Text"].lower()
    assert "quien te invitó" in mail["Text"]


async def test_en_la_fecha_se_crea_la_solicitud_y_el_worker_la_completa(
    committed_login: CommittedLogin,
    guests: Guests,
    uow_factory: Any,
    clock: FixedClock,
    app_engine: AsyncEngine,
) -> None:
    institutional, _ = await committed_login()
    teacher, _ = await committed_login(Role.TEACHER)
    guest, _ = await committed_login(guest=True)
    assert institutional.id and guest.id and teacher.id and guest.email
    await last_login(app_engine, institutional.id, clock.now() - timedelta(days=366))
    await guests.invitation(
        teacher.id, email=guest.email, status="revoked", guest_user_id=guest.id, access_days=10
    )
    # Revocada hace 91 días (antes de su vencimiento): el fin del acceso es la revocación.
    await sql(
        app_engine,
        "UPDATE identity.invitations SET revoked_at = :t WHERE guest_user_id = :g",
        t=clock.now() - timedelta(days=91),
        g=guest.id,
    )

    await process_retention(uow_factory=uow_factory, clock=clock)

    for user_id, origin in (
        (institutional.id, "institutional_retention"),
        (guest.id, "guest_retention"),
    ):
        request = await open_request(app_engine, user_id)
        assert request is not None, origin
        assert (request.origin, request.status) == (origin, "received")
        assert (
            await scalar(app_engine, "SELECT status FROM identity.users WHERE id = :u", u=user_id)
            == "deletion_pending"
        )
        (entry,) = await audits(app_engine, user_id, "deletion.requested")
        assert entry.actor_id is None and entry.details["origin"] == origin

    completed = await process_deletion_requests(uow_factory=uow_factory, clock=clock)

    assert completed >= 2
    for user_id in (institutional.id, guest.id):
        assert (await open_request(app_engine, user_id)).status == "completed"
        assert (
            await scalar(app_engine, "SELECT status FROM identity.users WHERE id = :u", u=user_id)
            == "deleted"
        )
        assert len(await audits(app_engine, user_id, "deletion.completed")) == 1


async def test_si_el_correo_falla_la_supresion_sigue(
    committed_login: CommittedLogin, uow_factory: Any, clock: FixedClock, app_engine: AsyncEngine
) -> None:
    user, _ = await committed_login()
    assert user.id is not None
    await last_login(app_engine, user.id, clock.now() - timedelta(days=336))
    await process_retention(uow_factory=uow_factory, clock=clock)
    (message,) = await notices(app_engine, user.id)

    with pytest.raises(ConnectionError):
        await handler_with(uow_factory, clock, FailingSender()).on_notice_due(message)
    assert await audits(app_engine, user.id, "retention.notice_sent") == []

    clock.advance(timedelta(days=30))
    await process_retention(uow_factory=uow_factory, clock=clock)

    request = await open_request(app_engine, user.id)
    assert request is not None and request.origin == "institutional_retention"


async def test_ingresar_antes_de_la_fecha_cancela_el_proceso(
    committed_login: CommittedLogin,
    uow_factory: Any,
    clock: FixedClock,
    handler: RetentionNoticeHandler,
    app_engine: AsyncEngine,
    mailpit: tuple[str, int, str],
) -> None:
    user, _ = await committed_login()
    assert user.id is not None and user.email is not None
    await last_login(app_engine, user.id, clock.now() - timedelta(days=340))
    await process_retention(uow_factory=uow_factory, clock=clock)
    (message,) = await notices(app_engine, user.id)

    # Ingresa antes de que el worker envíe el aviso (`record_login` limpia el aviso).
    await sql(
        app_engine,
        """UPDATE identity.users SET last_login_at = :t, retention_notice_sent_at = NULL
           WHERE id = :u""",
        t=clock.now(),
        u=user.id,
    )
    await handler.on_notice_due(message)
    clock.advance(timedelta(days=30))
    await process_retention(uow_factory=uow_factory, clock=clock)

    assert emails_to(mailpit[2], user.email, timeout=1) == []
    assert await open_request(app_engine, user.id) is None
    assert len(await notices(app_engine, user.id)) == 1


async def test_el_ultimo_administrador_activo_no_se_suprime(
    committed_login: CommittedLogin, uow_factory: Any, clock: FixedClock, app_engine: AsyncEngine
) -> None:
    admin, _ = await committed_login(Role.ADMIN)
    assert admin.id is not None
    await last_login(app_engine, admin.id, clock.now() - timedelta(days=400))

    await process_retention(uow_factory=uow_factory, clock=clock)
    await process_retention(uow_factory=uow_factory, clock=clock)

    assert await open_request(app_engine, admin.id) is None
    assert await notices(app_engine, admin.id) == []
    assert (
        await scalar(app_engine, "SELECT status FROM identity.users WHERE id = :u", u=admin.id)
        == "active"
    )
    (entry,) = await audits(app_engine, admin.id, "retention.skipped_last_admin")
    assert entry.actor_id is None

    # Con otro administrador activo, la regla general vuelve a aplicar.
    await committed_login(Role.ADMIN)
    await process_retention(uow_factory=uow_factory, clock=clock)
    request = await open_request(app_engine, admin.id)
    assert request is not None and request.origin == "institutional_retention"
