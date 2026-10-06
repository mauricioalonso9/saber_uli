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
