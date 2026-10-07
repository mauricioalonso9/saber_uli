"""Manejadores del outbox que emiten los enlaces de invitados y envían los correos (R-18, R-19).

Para `InvitationCreated` y `SignInLinkRequested`:

1. Comprueban que la invitación siga en un estado que lo permita (si cambió entre la solicitud
   y el procesamiento, no envían nada).
2. Invalidan los enlaces anteriores sin usar del mismo propósito, generan el token, guardan solo
   su hash y confirman.
3. Envían el correo con `<PUBLIC_BASE_URL>/acceso#t=<token>`. Si el envío falla, la excepción
   llega al despachador, que reintenta: el reintento emite otro enlace e invalida este.

El token en claro solo existe en esta función y en el correo; nunca se registra.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog

from saber_uli.identity.application.ports import LinkTokenGenerator
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.access_link import AccessLink, LinkPurpose, supersede_unused
from saber_uli.identity.domain.invitation import Invitation, InvitationStatus
from saber_uli.notifications.application.public import EmailService
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.infrastructure.outbox import OutboxMessage, OutboxRegistry

_log = structlog.get_logger(__name__)

COLOMBIA = timezone(timedelta(hours=-5), "America/Bogota")  # sin horario de verano
_MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

_TEMPLATES = {LinkPurpose.INVITATION: "guest_invitation", LinkPurpose.SIGN_IN: "guest_sign_in"}


def long_date(moment: datetime) -> str:
    local = moment.astimezone(COLOMBIA)
    return f"{local.day} de {_MONTHS[local.month - 1]} de {local.year}"


@dataclass(frozen=True)
class _Delivery:
    to: str
    template: str
    context: Mapping[str, Any]


class LinkEmailHandlers:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        email: EmailService,
        clock: Clock,
        tokens: LinkTokenGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._email = email
        self._clock = clock
        self._tokens = tokens

    def register(self, registry: OutboxRegistry) -> None:
        registry.register("identity.InvitationCreated", self.on_invitation_created)
        registry.register("identity.InvitationResent", self.on_invitation_created)
        registry.register("identity.SignInLinkRequested", self.on_sign_in_link_requested)

    async def on_invitation_created(self, message: OutboxMessage) -> None:
        await self._issue_and_send(_invitation_id(message), LinkPurpose.INVITATION)

    async def on_sign_in_link_requested(self, message: OutboxMessage) -> None:
        await self._issue_and_send(_invitation_id(message), LinkPurpose.SIGN_IN)

    async def _issue_and_send(self, invitation_id: UUID, purpose: LinkPurpose) -> None:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            invitation = await uow.invitations.get_for_update(invitation_id)
            if invitation is None or not _can_receive(invitation, purpose, now):
                _log.info("guest_link_skipped", purpose=purpose.value)
                return
            settings = await uow.settings.load()
            for previous in supersede_unused(
                await uow.access_links.unused_for(invitation_id, purpose), purpose, now
            ):
                await uow.access_links.save(previous)
            plaintext, token_hash = self._tokens.new()
            link = await uow.access_links.add(
                AccessLink.issue(
                    invitation_id, purpose, token_hash=token_hash, now=now, settings=settings
                )
            )
            if purpose is LinkPurpose.INVITATION:
                invitation.link_expires_at = link.expires_at
                await uow.invitations.save(invitation)
            await uow.invitations.set_delivery_status(invitation_id, "queued")
            delivery = _delivery(
                invitation,
                purpose,
                link,
                plaintext,
                settings_minutes=int((link.expires_at - now).total_seconds() // 60),
            )
            await uow.commit()

        try:
            await self._email.send_email(delivery.template, delivery.to, delivery.context)
        except Exception:
            await self._set_delivery(invitation_id, "failed")
            raise
        await self._set_delivery(invitation_id, "sent")

    async def _set_delivery(self, invitation_id: UUID, status: str) -> None:
        async with self._uow_factory() as uow:
            await uow.invitations.set_delivery_status(invitation_id, status)
            await uow.commit()


def _invitation_id(message: OutboxMessage) -> UUID:
    return UUID(str(message.payload["invitation_id"]))


def _can_receive(invitation: Invitation, purpose: LinkPurpose, now: datetime) -> bool:
    if invitation.email is None:
        return False
    if purpose is LinkPurpose.INVITATION:
        return (
            invitation.status is InvitationStatus.SENT
            and invitation.revoked_at is None
            and now < invitation.access_expires_at
        )
    return invitation.has_access(now)


def _delivery(
    invitation: Invitation,
    purpose: LinkPurpose,
    link: AccessLink,
    plaintext: str,
    *,
    settings_minutes: int,
) -> _Delivery:
    if invitation.email is None:
        raise ValueError("la invitación no tiene correo")
    context: dict[str, Any] = {
        "name": invitation.invitee_name,
        "link_path": f"/acceso#t={plaintext}",
        "access_until": long_date(invitation.access_expires_at),
    }
    if purpose is LinkPurpose.INVITATION:
        context["link_until"] = long_date(link.expires_at)
    else:
        context["link_minutes"] = settings_minutes
    return _Delivery(to=invitation.email, template=_TEMPLATES[purpose], context=context)
