"""Puertos de la capa de aplicación de `identity` (los implementa `identity.infrastructure`)."""

from typing import Protocol
from uuid import UUID

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
