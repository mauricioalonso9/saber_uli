"""T109: manejadores del worker que emiten enlaces y envían los correos (research R-18, R-19).

Al procesar `identity.SignInLinkRequested` o `identity.InvitationCreated`, el worker genera el
token, guarda solo su hash y envía el correo con `<PUBLIC_BASE_URL>/acceso#t=<token>`. El token
en claro no queda en la base de datos, en el outbox, en Redis ni en los logs.
"""

import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from structlog.testing import capture_logs

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.handlers.link_emails import LinkEmailHandlers
from saber_uli.identity.infrastructure.link_tokens import LinkTokenFactory, hash_link_token
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.notifications.application.public import EmailService
from saber_uli.notifications.infrastructure.smtp import SmtpEmailSender
from saber_uli.notifications.infrastructure.templates import JinjaTemplateRenderer
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from saber_uli.shared.infrastructure.outbox import OutboxMessage
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.guests import Guests

BASE_URL = "http://localhost"
LINK = re.compile(re.escape(BASE_URL) + r"/acceso#t=([A-Za-z0-9_-]{43})")


@pytest.fixture
async def teacher(committed_login: CommittedLogin) -> UUID:
    user, _ = await committed_login(Role.TEACHER)
    assert user.id is not None
    return user.id


@pytest.fixture
def handlers(app_engine: AsyncEngine, mailpit: tuple[str, int, str]) -> LinkEmailHandlers:
    host, port, _ = mailpit
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    return LinkEmailHandlers(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
        email=EmailService(
            renderer=JinjaTemplateRenderer(public_base_url=BASE_URL),
            sender=SmtpEmailSender(
                host=host,
                port=port,
                sender="Saber Uli <no-responder@unilibre.edu.co>",
                starttls=False,
            ),
        ),
        clock=SystemClock(),
        tokens=LinkTokenFactory(),
    )


def message(event_type: str, invitation_id: UUID) -> OutboxMessage:
    return OutboxMessage(
        event_id=uuid4(),
        event_type=event_type,
        context="identity",
        payload={"invitation_id": str(invitation_id)},
        occurred_at=datetime.now(UTC),
        attempt=1,
    )


def emails_to(api: str, address: str, count: int = 1, timeout: float = 10) -> list[dict[str, Any]]:
    """Espera `count` correos para `address` y los devuelve del más reciente al más antiguo."""
    deadline = time.monotonic() + timeout
    while True:
        found = httpx.get(
            f"{api}/api/v1/search", params={"query": f'to:"{address}"'}, timeout=5
        ).json()["messages"]
        if len(found) >= count or time.monotonic() > deadline:
            break
        time.sleep(0.2)
    return [httpx.get(f"{api}/api/v1/message/{item['ID']}", timeout=5).json() for item in found]


def token_in(mail: dict[str, Any]) -> str:
    html, plain = LINK.search(mail["HTML"]), LINK.search(mail["Text"])
    assert html and plain, "el correo no trae el enlace /acceso#t=…"
    assert html.group(1) == plain.group(1)
    return html.group(1)


async def link_row(engine: AsyncEngine, token: str) -> Any:
    async with engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    "SELECT purpose, expires_at, used_at, created_at FROM identity.access_links"
                    " WHERE token_hash = :h"
                ),
                {"h": hash_link_token(token)},
            )
        ).one_or_none()


async def active_guest(
    api_client: httpx.AsyncClient, guests: Guests, teacher: UUID
) -> tuple[UUID, str]:
    invitation_id, email = await guests.invitation(teacher)
    token = await guests.link(invitation_id)
    assert (
        await api_client.post("/api/auth/guest/sessions", json={"token": token})
    ).status_code == 200
    return invitation_id, email


async def assert_token_not_stored(
    token: str, engine: AsyncEngine, redis_client: Redis, logs: list[dict[str, Any]]
) -> None:
    async with engine.connect() as conn:
        outbox = (
            await conn.execute(text("SELECT payload::text FROM shared.outbox_events"))
        ).scalars()
        assert all(token not in payload for payload in outbox)
        stored = (
            await conn.execute(
                text("SELECT count(*) FROM identity.access_links WHERE token_hash = :raw"),
                {"raw": token.encode()},
            )
        ).scalar_one()
        assert stored == 0
    async for key in redis_client.scan_iter():
        assert token.encode() not in key
        value = await redis_client.dump(key)
        assert value is None or token.encode() not in value
    assert token not in repr(logs)


async def test_el_enlace_de_ingreso_llega_por_correo_y_solo_queda_su_hash(
    handlers: LinkEmailHandlers,
    api_client: httpx.AsyncClient,
    guests: Guests,
    teacher: UUID,
    app_engine: AsyncEngine,
    redis_client: Redis,
    mailpit: tuple[str, int, str],
) -> None:
    invitation_id, email = await active_guest(api_client, guests, teacher)

    with capture_logs() as logs:
        await handlers.on_sign_in_link_requested(
            message("identity.SignInLinkRequested", invitation_id)
        )

    [mail] = emails_to(mailpit[2], email)
    assert [to["Address"] for to in mail["To"]] == [email]
    assert "ingresar" in mail["Subject"].lower()
    token = token_in(mail)
    row = await link_row(app_engine, token)
    assert row is not None and row.purpose == "sign_in" and row.used_at is None
    assert row.expires_at - row.created_at == timedelta(minutes=15)
    await assert_token_not_stored(token, app_engine, redis_client, logs)

    response = await api_client.post("/api/auth/guest/sessions", json={"token": token})
    assert response.status_code == 200, response.text


async def test_un_enlace_nuevo_invalida_el_anterior(
    handlers: LinkEmailHandlers,
    api_client: httpx.AsyncClient,
    guests: Guests,
    teacher: UUID,
    mailpit: tuple[str, int, str],
) -> None:
    invitation_id, email = await active_guest(api_client, guests, teacher)

    await handlers.on_sign_in_link_requested(message("identity.SignInLinkRequested", invitation_id))
    await handlers.on_sign_in_link_requested(message("identity.SignInLinkRequested", invitation_id))

    newest, older = (token_in(mail) for mail in emails_to(mailpit[2], email, count=2))
    assert newest != older
    old = await api_client.post("/api/auth/guest/sessions", json={"token": older})
    assert old.status_code == 400
    assert (
        await api_client.post("/api/auth/guest/sessions", json={"token": newest})
    ).status_code == 200


async def test_la_invitacion_llega_por_correo_con_su_enlace_de_7_dias(
    handlers: LinkEmailHandlers,
    guests: Guests,
    teacher: UUID,
    app_engine: AsyncEngine,
    mailpit: tuple[str, int, str],
) -> None:
    invitation_id, email = await guests.invitation(teacher)

    await handlers.on_invitation_created(message("identity.InvitationCreated", invitation_id))

    [mail] = emails_to(mailpit[2], email)
    assert "invitación" in mail["Subject"].lower()
    token = token_in(mail)
    row = await link_row(app_engine, token)
    assert row is not None and row.purpose == "invitation"
    assert row.expires_at - row.created_at == timedelta(days=7)
    async with app_engine.connect() as conn:
        invitation = (
            await conn.execute(
                text(
                    "SELECT link_expires_at, last_delivery_status FROM identity.invitations"
                    " WHERE id = :id"
                ),
                {"id": invitation_id},
            )
        ).one()
    assert invitation.link_expires_at == row.expires_at
    assert invitation.last_delivery_status == "sent"


async def test_sin_acceso_vigente_no_envia_nada(
    handlers: LinkEmailHandlers,
    api_client: httpx.AsyncClient,
    guests: Guests,
    teacher: UUID,
    mailpit: tuple[str, int, str],
) -> None:
    # Se revocó el acceso entre la solicitud y el procesamiento.
    invitation_id, email = await active_guest(api_client, guests, teacher)
    async with guests.engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE identity.invitations SET status = 'revoked', revoked_at = now()"
                " WHERE id = :id"
            ),
            {"id": invitation_id},
        )

    await handlers.on_sign_in_link_requested(message("identity.SignInLinkRequested", invitation_id))

    assert emails_to(mailpit[2], email, timeout=1) == []
