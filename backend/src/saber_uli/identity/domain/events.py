"""Eventos de dominio de `identity` (data-model §6). Solo llevan identificadores."""

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from saber_uli.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserAccessChanged(DomainEvent):
    """Cambió la época de autorización del usuario (desactivación, revocación, retiro de roles,
    supresión). Tras el commit se invalida la caché de `auth_epoch` (R-16)."""

    event_type: ClassVar[str] = "identity.UserAccessChanged"
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class InvitationCreated(DomainEvent):
    """Se creó (o reenvió) una invitación: el worker emite el enlace y envía el correo (R-19)."""

    event_type: ClassVar[str] = "identity.InvitationCreated"
    invitation_id: UUID


@dataclass(frozen=True, kw_only=True)
class SignInLinkRequested(DomainEvent):
    """Un invitado vigente pidió un enlace de ingreso (FR-013). Sin correo ni token (R-19)."""

    event_type: ClassVar[str] = "identity.SignInLinkRequested"
    invitation_id: UUID
