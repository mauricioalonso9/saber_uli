"""Eventos de `identity` que viajan por el outbox transaccional (research R-08, R-19)."""

from saber_uli.identity.domain.events import InvitationCreated, SignInLinkRequested
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.outbox import register_outbox


def register_identity_outbox(bus: EventBus) -> None:
    """Escribe en el outbox, dentro de la transacción de la acción, los eventos que procesa el
    worker (correos con enlaces de invitados)."""
    register_outbox(bus, InvitationCreated, SignInLinkRequested, context="identity")
