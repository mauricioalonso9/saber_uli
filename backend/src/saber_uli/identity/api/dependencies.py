"""Dependencias comunes de las rutas de gestión: permiso del contrato y sesión privilegiada.

Primero el permiso (403 `forbidden`) y después la sesión privilegiada (401
`reauthentication-required`, R-15), como en el resto de la API.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.permissions import Permission
from saber_uli.shared.api.auth import require_permission, require_privileged


def privileged_with(*permissions: Permission) -> Callable[..., Awaitable[AuthenticatedUser]]:
    allowed = require_permission(*(permission.value for permission in permissions))

    async def dependency(
        user: Annotated[AuthenticatedUser, Depends(allowed)],
        _: Annotated[AuthenticatedUser, Depends(require_privileged)],
    ) -> AuthenticatedUser:
        return user

    return dependency
