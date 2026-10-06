"""Puertos de la capa de aplicación de `identity` (los implementa `identity.infrastructure`)."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from saber_uli.identity.domain.session import RefreshToken, RevocationReason, Session
from saber_uli.identity.domain.user import InstitutionalIdentity, User


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
