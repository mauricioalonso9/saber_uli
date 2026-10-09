"""Fachada pública del contexto `identity` (research R-04).

Es lo único que otros contextos y el kernel compartido pueden importar de `identity`.

- `AuthenticatedUser` y `Authenticator`: los usa `shared/api/auth.py` (T048). La implementación
  (`identity.application.access_guard.AccessGuard`) la arma `main.py` (T058) y la deja en
  `app.state.authenticator`.
- `ConsentChecker`: lo usa `shared/api/consent_guard.py` (T052); lo implementa
  `identity.application.queries.consent_status.ConsentStatusQuery`.
- `UserDirectory` (`is_institutional`, `is_guest`): las ligas y la analítica de programa excluyen
  a los invitados (FR-012). Lo implementa `identity.application.directory.IdentityDirectory`.
  `director_program_ids` da los programas de un director, para la analítica agregada (FR-026).
  `display_names` da los nombres de autores y revisores del banco de ítems (002/R-14).
"""

from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AuthenticatedUser:
    """Usuario de la petición, según su token de acceso ya validado."""

    id: UUID
    session_id: UUID
    roles: frozenset[str]
    privileged: bool
    permissions: frozenset[str] = frozenset()


class Authenticator(Protocol):
    async def authenticate(self, token: str) -> AuthenticatedUser:
        """Valida el token y la época vigente; lanza un error 401 con la causa (R-16)."""
        ...

    async def record_privileged_activity(self, user: AuthenticatedUser) -> None:
        """Extiende la ventana de 30 minutos de la sesión privilegiada (R-15)."""
        ...


class ConsentChecker(Protocol):
    async def has_current_consent(self, user_id: UUID) -> bool:
        """Autorización de datos vigente (FR-014)."""
        ...


class UserDirectory(Protocol):
    async def is_institutional(self, user_id: UUID) -> bool:
        """Cuenta institucional de Unilibre (falso si no existe)."""
        ...

    async def is_guest(self, user_id: UUID) -> bool:
        """Invitado: no aparece en ligas institucionales ni en analítica (FR-012)."""
        ...

    async def director_program_ids(self, user_id: UUID) -> set[UUID]:
        """Programas que dirige (vacío si no es Director de programa)."""
        ...

    async def display_names(self, user_ids: Collection[UUID]) -> dict[UUID, str]:
        """Nombre para mostrar de cada cuenta existente, en una sola consulta (002/R-14).

        Una cuenta suprimida aparece como "Cuenta eliminada"; los identificadores desconocidos
        se omiten. `content` guarda solo identificadores y pide los nombres aquí.
        """
        ...

    async def active_admin_ids(self) -> set[UUID]:
        """Administradores activos: la cola de revisión del banco marca los ítems que ninguno
        puede aprobar porque todos los modificaron (002 FR-012)."""
        ...
