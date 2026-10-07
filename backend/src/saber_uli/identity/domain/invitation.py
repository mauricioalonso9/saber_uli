"""Invitaciones y acceso de invitados (FR-006 a FR-011; data-model §2.7 y §4.2).

```text
sent ──(consumo del enlace)──► accepted ──(vence)──► expired
  └─────────── revocar ──────────┴──► revoked
```

El acceso de un invitado está vigente si la invitación está aceptada, no fue revocada y
`access_expires_at` aún no llega. El fin del acceso es el mínimo entre la revocación y el
vencimiento. Los errores de acceso los comparten el ingreso con el enlace (403) y la renovación
de la sesión (401).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.domain.user import User
from saber_uli.shared.domain.errors import (
    ConflictError,
    NotFoundError,
    RuleViolationError,
    UnauthenticatedError,
)


class InvitationStatus(StrEnum):
    SENT = "sent"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class GuestAccessExpiredError(UnauthenticatedError):
    slug = "guest-access-expired"


class GuestAccessRevokedError(UnauthenticatedError):
    slug = "guest-access-revoked"


class AccessExpiryOutOfRangeError(RuleViolationError):
    slug = "access-expiry-out-of-range"


class InvitationNotPendingError(ConflictError):
    slug = "invitation-not-pending"


class InvitationAlreadyActiveError(ConflictError):
    slug = "invitation-already-active"


class InvitationAlreadyRevokedError(ConflictError):
    slug = "invitation-already-revoked"


class InvitationNotRenewableError(ConflictError):
    """Pasaron más de 90 días desde el fin del acceso, o nunca se aceptó y fue revocada."""

    slug = "invitation-not-renewable"


class GuestErasedError(ConflictError):
    """El invitado ya fue suprimido: una invitación nueva crearía otro usuario."""

    slug = "guest-erased"


class InvitationNotFoundError(NotFoundError):
    """No existe o no es de quien consulta (un docente solo ve las suyas: escenario 5.7)."""

    slug = "not-found"


RENEWAL_WINDOW = timedelta(days=90)


def validate_access_expiry(
    expires_at: datetime, *, now: datetime, is_admin: bool, settings: IdentitySettings
) -> None:
    """FR-006a: futuro y, si no invita un administrador, dentro del plazo máximo del docente."""
    if expires_at <= now:
        raise AccessExpiryOutOfRangeError("El acceso debe vencer en una fecha futura.")
    if not is_admin and expires_at > now + settings.teacher_max_access:
        raise AccessExpiryOutOfRangeError(
            f"El acceso puede durar como máximo {settings.teacher_max_access_days} días."
        )


class InstitutionalEmailNotInvitableError(RuleViolationError):
    """FR-008: la comunidad Unilibre ingresa con su cuenta, no por invitación."""

    slug = "institutional-email-not-invitable"


def is_institutional_email(email: str, domains: Iterable[str]) -> bool:
    """El dominio del correo es uno institucional o un subdominio suyo (R-20)."""
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return any(
        domain == allowed or domain.endswith(f".{allowed}")
        for allowed in (d.strip().lower() for d in domains)
        if allowed
    )


@dataclass(eq=False)
class Invitation:
    email: str | None
    invited_by: UUID | None  # `None`: el sistema (comando `invite-guest`)
    access_expires_at: datetime
    status: InvitationStatus
    created_at: datetime
    id: UUID | None = None
    invitee_name: str | None = None
    batch_id: UUID | None = None
    guest_user_id: UUID | None = None
    link_expires_at: datetime | None = None
    sent_at: datetime | None = None
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        email: str,
        invited_by: UUID | None,
        access_expires_at: datetime,
        now: datetime,
        invitee_name: str | None = None,
        batch_id: UUID | None = None,
    ) -> "Invitation":
        if access_expires_at <= now:
            raise AccessExpiryOutOfRangeError("El acceso debe vencer en una fecha futura.")
        return cls(
            email=email.strip(),
            invited_by=invited_by,
            access_expires_at=access_expires_at,
            status=InvitationStatus.SENT,
            created_at=now,
            invitee_name=(invitee_name or "").strip() or None,
            batch_id=batch_id,
            sent_at=now,
        )

    # --- Consultas ------------------------------------------------------------------------

    @property
    def access_ends_at(self) -> datetime:
        if self.revoked_at is not None and self.revoked_at < self.access_expires_at:
            return self.revoked_at
        return self.access_expires_at

    def has_access(self, now: datetime) -> bool:
        return (
            self.status is InvitationStatus.ACCEPTED
            and self.revoked_at is None
            and now < self.access_expires_at
        )

    def ensure_access(self, now: datetime) -> None:
        """Lanza la causa si el invitado no puede ingresar (FR-011)."""
        if self.status is InvitationStatus.REVOKED or self.revoked_at is not None:
            raise GuestAccessRevokedError("Tu acceso como invitado fue retirado.")
        if self.status is InvitationStatus.EXPIRED or now >= self.access_expires_at:
            raise GuestAccessExpiredError("Tu acceso como invitado venció.")

    # --- Transiciones ---------------------------------------------------------------------

    def new_guest_user(self, now: datetime) -> User:
        """Cuenta del invitado al aceptar: solo el rol Invitado (FR-024)."""
        if self.email is None:
            raise ValueError("la invitación ya no tiene correo")
        return User.new_guest(email=self.email, display_name=self.invitee_name, now=now)

    def accept(self, guest_user_id: UUID, now: datetime) -> None:
        self.ensure_access(now)
        if self.status is not InvitationStatus.SENT:
            raise InvitationNotPendingError("La invitación ya fue aceptada.")
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = now
        self.guest_user_id = guest_user_id

    def revoke(self, now: datetime) -> None:
        if self.status is InvitationStatus.REVOKED:
            raise InvitationAlreadyRevokedError("La invitación ya estaba revocada.")
        self.status = InvitationStatus.REVOKED
        self.revoked_at = now

    def resend(self, now: datetime) -> None:
        """Solo sin aceptar ni revocar (§4.2): vuelve a `sent`; el worker emite otro enlace."""
        if self.accepted_at is not None or self.status in (
            InvitationStatus.ACCEPTED,
            InvitationStatus.REVOKED,
        ):
            raise InvitationNotPendingError("Solo se reenvían invitaciones sin aceptar.")
        if now >= self.access_expires_at:
            raise AccessExpiryOutOfRangeError(
                "El acceso de esta invitación ya venció: amplía primero su vencimiento."
            )
        self.status = InvitationStatus.SENT
        self.sent_at = now

    def change_expiry(self, access_expires_at: datetime, now: datetime) -> bool:
        """Amplía, reduce o renueva el acceso (escenario 5.5). Devuelve si fue una renovación:
        una invitación aceptada cuyo acceso terminó hace 90 días o menos vuelve a `accepted`."""
        if self.accepted_at is None:
            if self.status is InvitationStatus.REVOKED:
                raise InvitationNotRenewableError(
                    "Esta invitación fue revocada antes de aceptarse: envía una nueva."
                )
            self.access_expires_at = access_expires_at
            return False
        if self.status is InvitationStatus.ACCEPTED and self.revoked_at is None:
            self.access_expires_at = access_expires_at
            return False
        if now - self.access_ends_at > RENEWAL_WINDOW:
            raise InvitationNotRenewableError(
                "Pasaron más de 90 días desde el fin del acceso: envía una invitación nueva."
            )
        self.status = InvitationStatus.ACCEPTED
        self.revoked_at = None
        self.access_expires_at = access_expires_at
        return True
