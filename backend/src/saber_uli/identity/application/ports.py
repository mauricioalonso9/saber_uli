"""Puertos de la capa de aplicación de `identity` (los implementa `identity.infrastructure`)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from saber_uli.identity.domain.consent import ConsentDecision, ConsentRecord
from saber_uli.identity.domain.policy import PolicyVersion
from saber_uli.identity.domain.session import RefreshToken, RevocationReason, Session
from saber_uli.identity.domain.user import InstitutionalIdentity, User

if TYPE_CHECKING:
    from saber_uli.identity.application.audit import AuditEntry

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


class SessionRevocations(Protocol):
    """Sesiones revocadas cuyo token de acceso aún no vence (ASVS V3.3.1). Nunca lanza."""

    async def revoke(self, session_id: UUID) -> None: ...

    async def is_revoked(self, session_id: UUID) -> bool: ...


class GuestAccessStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    NONE = "none"


class GuestAccessReader(Protocol):
    async def status_for(self, user_id: UUID, *, now: datetime) -> GuestAccessStatus:
        """Estado del acceso derivado de la invitación más reciente del invitado (§4.2)."""
        ...

    async def expires_at_for(self, user_id: UUID) -> datetime | None:
        """Vencimiento del acceso según la invitación más reciente (`None` si no hay)."""
        ...


class AuditRepository(Protocol):
    async def add(self, entry: "AuditEntry") -> None: ...


@dataclass(frozen=True)
class ConsentEntry:
    """Registro guardado de una decisión, con la versión de la política (esquema `Consent`)."""

    id: UUID
    policy_version_id: UUID
    policy_version: str
    decision: ConsentDecision
    channel: str
    decided_at: datetime


class ConsentRepository(Protocol):
    """Autorizaciones de datos: solo inserción y lectura (data-model §2.11)."""

    async def latest_for_user(self, user_id: UUID) -> ConsentRecord | None: ...

    async def current_policy_version_id(self, *, now: datetime) -> UUID | None: ...

    async def history_for_user(self, user_id: UUID) -> list[ConsentEntry]:
        """Decisiones del usuario, de la más reciente a la más antigua."""
        ...

    async def add(self, user_id: UUID, record: ConsentRecord) -> ConsentEntry: ...


class PolicyRepository(Protocol):
    """Versiones de la política: solo inserción y lectura (data-model §2.10)."""

    async def current(self, *, now: datetime) -> PolicyVersion | None:
        """La de mayor `effective_from ≤ now`."""
        ...

    async def get(self, version_id: UUID) -> PolicyVersion | None: ...

    async def versions(self) -> set[str]: ...

    async def latest_effective_from(self) -> datetime | None:
        """Mayor `effective_from` entre todas las versiones, incluidas las programadas."""
        ...

    async def add(self, version: PolicyVersion) -> PolicyVersion:
        """Guarda la versión y la devuelve con su `id`.

        Lanza `PolicyVersionExistsError` si otra transacción publicó la misma versión.
        """
        ...


class UserAlreadyExistsError(Exception):
    """Otra transacción ya creó la cuenta con la misma identidad institucional."""


class UserRepository(Protocol):
    async def add(self, user: User) -> User:
        """Guarda un usuario nuevo y le asigna el `id` generado por la base de datos.

        Lanza `UserAlreadyExistsError` si la identidad (`tid`, `oid`) ya existe.
        """
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
