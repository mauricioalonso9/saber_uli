"""Dependencias de autenticación de FastAPI (research R-14 a R-16).

- `current_user`: exige `Authorization: Bearer <token>` y lo valida con el autenticador de
  `identity` (`app.state.authenticator`, lo arma `main.py` en T058). Sin token o con un token
  inválido responde 401 `unauthenticated` con `WWW-Authenticate: Bearer`; con la época vencida,
  401 con la causa (`account-disabled`, `session-revoked`…).
- `require_privileged`: para las rutas `x-requires-privileged-session`. Sin `priv` responde 401
  `reauthentication-required`; con `priv`, registra la actividad privilegiada (R-15).
- `require_permission(*permisos)`: niega por defecto (ASVS V4.1.3, FR-030); basta uno de
  los permisos del contrato (`users:manage`…). Sin él responde 403 `forbidden`. El alcance
  (recursos propios) lo verifica cada caso de uso y responde 404 fuera de alcance (R-22).
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, Request

from saber_uli.identity.application.public import AuthenticatedUser, Authenticator
from saber_uli.shared.api.problems import ProblemException

_BEARER = "bearer"
_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def _authenticator(request: Request) -> Authenticator:
    authenticator: Authenticator = request.app.state.authenticator
    return authenticator


def _unauthenticated() -> ProblemException:
    return ProblemException(
        401, "unauthenticated", detail="Inicia sesión para continuar.", headers=_CHALLENGE
    )


async def current_user(
    authenticator: Annotated[Authenticator, Depends(_authenticator)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != _BEARER or not token.strip():
        raise _unauthenticated()
    return await authenticator.authenticate(token.strip())


async def require_privileged(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
    authenticator: Annotated[Authenticator, Depends(_authenticator)],
) -> AuthenticatedUser:
    if not user.privileged:
        raise ProblemException(
            401,
            "reauthentication-required",
            detail="Por seguridad, vuelve a ingresar para usar esta función.",
        )
    await authenticator.record_privileged_activity(user)
    return user


def require_permission(*permissions: str) -> Callable[..., Awaitable[AuthenticatedUser]]:
    if not permissions:
        raise ValueError("indique al menos un permiso")
    required = frozenset(permissions)

    async def dependency(
        user: Annotated[AuthenticatedUser, Depends(current_user)],
    ) -> AuthenticatedUser:
        if not required & user.permissions:
            raise ProblemException(403, "forbidden", detail="No tienes permiso para esta función.")
        return user

    return dependency
