"""Enlaces de acceso de invitados (FR-007, FR-013; research R-18, R-19; data-model §2.8).

Cada enlace es de un solo uso y vence: 7 días el de invitación y 10 minutos el de ingreso (por
defecto; ambos son parámetros). Del token solo se guarda su SHA-256. Emitir un enlace nuevo
invalida los anteriores sin usar de la misma invitación y propósito.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.shared.domain.errors import RuleViolationError


class LinkPurpose(StrEnum):
    INVITATION = "invitation"
    SIGN_IN = "sign_in"


class AccessLinkInvalidError(RuleViolationError):
    """Enlace inexistente, ya usado o vencido (400 en el contrato)."""

    slug = "access-link-invalid"


@dataclass(eq=False)
class AccessLink:
    invitation_id: UUID
    purpose: LinkPurpose
    token_hash: bytes
    expires_at: datetime
    created_at: datetime
    id: UUID | None = None
    used_at: datetime | None = None

    @classmethod
    def issue(
        cls,
        invitation_id: UUID,
        purpose: LinkPurpose,
        *,
        token_hash: bytes,
        now: datetime,
        settings: IdentitySettings,
    ) -> "AccessLink":
        ttl = (
            settings.invitation_link_ttl
            if purpose is LinkPurpose.INVITATION
            else settings.sign_in_link_ttl
        )
        return cls(
            invitation_id=invitation_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=now + ttl,
            created_at=now,
        )

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at

    def consume(self, now: datetime) -> None:
        if not self.is_usable(now):
            raise AccessLinkInvalidError("El enlace no es válido, ya se usó o venció.")
        self.used_at = now


def supersede_unused(
    links: Iterable[AccessLink], purpose: LinkPurpose, now: datetime
) -> list[AccessLink]:
    """Invalida los enlaces sin usar de `purpose`; devuelve los que cambió."""
    superseded = [link for link in links if link.purpose is purpose and link.used_at is None]
    for link in superseded:
        link.used_at = now
    return superseded
