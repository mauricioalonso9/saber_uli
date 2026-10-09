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


@dataclass(frozen=True, kw_only=True)
class InvitationResent(DomainEvent):
    """Se reenvió una invitación sin aceptar: el worker emite un enlace nuevo (R-19)."""

    event_type: ClassVar[str] = "identity.InvitationResent"
    invitation_id: UUID


@dataclass(frozen=True, kw_only=True)
class DeletionRequested(DomainEvent):
    """Se abrió una solicitud de supresión (voluntaria o por conservación): el worker la procesa
    sin esperar a la tarea periódica (R-25)."""

    event_type: ClassVar[str] = "identity.DeletionRequested"
    user_id: UUID
    deletion_request_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserErased(DomainEvent):
    """Terminó la supresión: los demás contextos anonimizan lo suyo (consumidores en 002+)."""

    event_type: ClassVar[str] = "identity.UserErased"
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class RetentionNoticeDue(DomainEvent):
    """Toca el aviso de supresión automática en 30 días (FR-034c). El correo destino y las
    fechas se leen en el manejador, justo antes de enviar."""

    event_type: ClassVar[str] = "identity.RetentionNoticeDue"
    user_id: UUID
