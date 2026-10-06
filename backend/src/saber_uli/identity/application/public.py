"""Fachada pública del contexto `identity` (research R-04).

Es lo único que otros contextos y el kernel compartido pueden importar de `identity`.

- `AuthenticatedUser` y `Authenticator`: los usa `shared/api/auth.py` (T048). La implementación
  (`identity.application.access_guard.AccessGuard`) la arma `main.py` (T058) y la deja en
  `app.state.authenticator`.
- `ConsentChecker`: lo usa `shared/api/consent_guard.py` (T052); lo implementa
  `identity.application.queries.consent_status.ConsentStatusQuery`.
- `is_institutional`, `is_guest` y `director_program_ids` llegan con T117 y T145.
"""

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
