"""Sesiones y tokens de renovación (research R-14, R-15; data-model §2.13; FR-037, FR-038).

- Sesión de aprendizaje: 7 días de inactividad (vigencia de cada token de renovación) y 30 días
  absolutos desde el ingreso.
- Cada renovación rota el token. Presentar un token ya rotado revoca la sesión completa (la
  "familia": todos los tokens derivados de ese ingreso).
- Sesión privilegiada (`priv`): rol con privilegios, autenticación real hace menos de 12 horas y
  actividad privilegiada hace menos de 30 minutos. Al crear la sesión o reautenticarse, la
  actividad privilegiada parte de `auth_time`.

El dominio no conoce JWT ni hashes: recibe el hash del token ya calculado (infraestructura).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from uuid import UUID

from saber_uli.identity.domain.roles import Role, has_privileged_role
from saber_uli.shared.domain.errors import UnauthenticatedError

IDLE_TIMEOUT = timedelta(days=7)
ABSOLUTE_LIFETIME = timedelta(days=30)
PRIVILEGED_REAUTHENTICATION = timedelta(hours=12)
PRIVILEGED_IDLE = timedelta(minutes=30)

RevocationReason = Literal["logout", "token_reuse", "access_changed", "reauthenticated"]


class AuthMethod(StrEnum):
    ENTRA_ID = "entra_id"
    GUEST_LINK = "guest_link"


class SessionExpiredError(UnauthenticatedError):
    slug = "session-expired"


class SessionRevokedError(UnauthenticatedError):
    slug = "session-revoked"


@dataclass(eq=False)
class Session:
    user_id: UUID
    auth_method: AuthMethod
    auth_time: datetime
    last_seen_at: datetime
    last_privileged_activity_at: datetime | None
    absolute_expires_at: datetime
    id: UUID | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None

    @classmethod
    def start(cls, user_id: UUID, method: AuthMethod, now: datetime) -> "Session":
        return cls(
            user_id=user_id,
            auth_method=method,
            auth_time=now,
            last_seen_at=now,
            last_privileged_activity_at=now,
            absolute_expires_at=now + ABSOLUTE_LIFETIME,
        )

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.absolute_expires_at

    def is_privileged(self, now: datetime, *, roles: Iterable[Role]) -> bool:
        if not has_privileged_role(roles) or self.last_privileged_activity_at is None:
            return False
        return (
            now - self.auth_time < PRIVILEGED_REAUTHENTICATION
            and now - self.last_privileged_activity_at < PRIVILEGED_IDLE
        )

    def touch(self, now: datetime) -> None:
        self.last_seen_at = now

    def record_privileged_activity(self, now: datetime) -> None:
        self.last_privileged_activity_at = now

    def reauthenticate(self, now: datetime) -> None:
        self.auth_time = now
        self.last_privileged_activity_at = now

    def revoke(self, now: datetime, reason: RevocationReason) -> None:
        if self.revoked_at is None:
            self.revoked_at = now
            self.revoked_reason = reason


@dataclass(eq=False)
class RefreshToken:
    session_id: UUID
    token_hash: bytes
    issued_at: datetime
    idle_expires_at: datetime
    rotated_at: datetime | None = None
    id: UUID | None = None

    @classmethod
    def issue(cls, session: Session, *, token_hash: bytes, now: datetime) -> "RefreshToken":
        if session.id is None:
            raise ValueError("la sesión debe estar guardada antes de emitir tokens")
        return cls(
            session_id=session.id,
            token_hash=token_hash,
            issued_at=now,
            # La inactividad no extiende la sesión más allá de su límite absoluto.
            idle_expires_at=min(now + IDLE_TIMEOUT, session.absolute_expires_at),
        )


def rotate_refresh_token(
    session: Session, current: RefreshToken, *, new_hash: bytes, now: datetime
) -> RefreshToken:
    """Valida `current`, lo marca como rotado y emite el siguiente token de la familia.

    Lanza `SessionRevokedError` si la sesión estaba revocada o si `current` ya se había usado
    (reutilización: revoca la sesión), y `SessionExpiredError` si venció por inactividad o por
    duración absoluta.
    """
    if current.rotated_at is not None:
        session.revoke(now, "token_reuse")
        raise SessionRevokedError("La sesión se cerró por seguridad.")
    if session.revoked_at is not None:
        raise SessionRevokedError("La sesión se cerró.")
    if now >= current.idle_expires_at or not session.is_active(now):
        raise SessionExpiredError("La sesión venció.")
    current.rotated_at = now
    session.touch(now)
    return RefreshToken.issue(session, token_hash=new_hash, now=now)
