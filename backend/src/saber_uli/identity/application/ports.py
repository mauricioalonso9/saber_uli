"""Puertos de la capa de aplicación de `identity` (los implementa `identity.infrastructure`)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from saber_uli.identity.domain.session import RefreshToken, RevocationReason, Session
from saber_uli.identity.domain.user import InstitutionalIdentity, User

ACCESS_TOKEN_TTL_SECONDS = 600


@dataclass(frozen=True)
class AccessTokenClaims:
    """Contenido del token de acceso (R-14)."""

    sub: UUID
    sid: UUID
    roles: tuple[str, ...]
    epoch: int
    priv: bool
    iat: datetime

    @property
    def expires_at(self) -> datetime:
        return self.iat + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)


class AccessTokenEncoder(Protocol):
    def encode(self, claims: AccessTokenClaims) -> str: ...


class RefreshTokenGenerator(Protocol):
    def new(self) -> tuple[str, bytes]:
        """Token en claro (solo para la cookie) y su hash (solo para la base de datos)."""
        ...

    def hash(self, plaintext: str) -> bytes: ...


class AccessTokenDecoder(Protocol):
    def decode(self, token: str, *, now: datetime) -> AccessTokenClaims:
        """Lanza un `UnauthenticatedError` si el token no es válido o venció."""
        ...


class EpochStore(Protocol):
    """Caché de `auth_epoch` por usuario (R-16). Nunca lanza: si falla, se comporta como vacía."""

    async def get(self, user_id: UUID) -> int | None: ...

    async def set(self, user_id: UUID, epoch: int) -> None: ...

    async def invalidate(self, user_id: UUID) -> None: ...


class GuestAccessStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    NONE = "none"


class GuestAccessReader(Protocol):
    async def status_for(self, user_id: UUID, *, now: datetime) -> GuestAccessStatus:
        """Estado del acceso derivado de la invitación más reciente del invitado (§4.2)."""
        ...


class UserRepository(Protocol):
    async def add(self, user: User) -> User:
        """Guarda un usuario nuevo y le asigna el `id` generado por la base de datos."""
        ...

    async def save(self, user: User) -> None:
        """Persiste los cambios de un usuario existente (estado, época, datos y roles)."""
        ...

    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_entra_identity(self, identity: InstitutionalIdentity) -> User | None: ...

    async def find_active_guest_by_email(self, email: str) -> User | None:
        """Invitado no suprimido con ese correo, sin distinguir mayúsculas."""
        ...

    async def lock_active_admins(self) -> list[UUID]:
        """Bloquea (`FOR UPDATE`) y devuelve los administradores activos (FR-025, FR-034d)."""
        ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> Session: ...

    async def save(self, session: Session) -> None: ...

    async def get(self, session_id: UUID) -> Session | None: ...

    async def add_refresh_token(self, token: RefreshToken) -> RefreshToken: ...

    async def save_refresh_token(self, token: RefreshToken) -> None: ...

    async def get_refresh_token_for_update(self, token_hash: bytes) -> RefreshToken | None:
        """Token por su hash, bloqueado hasta el fin de la transacción."""
        ...

    async def revoke_all_for_user(
        self, user_id: UUID, *, now: datetime, reason: RevocationReason
    ) -> int:
        """Revoca las sesiones activas del usuario (al incrementar `auth_epoch`, R-16)."""
        ...
