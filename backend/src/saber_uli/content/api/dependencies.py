"""Dependencias de las rutas del banco de ítems (research R-08).

Primero el permiso (403 `forbidden`) y después la sesión privilegiada (401
`reauthentication-required`, 001/R-15), como en el resto de la API. Los permisos se nombran como en
el contrato; `content` no importa el dominio de `identity` (principio II).
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant

from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.shared.api.auth import require_permission, require_privileged
from saber_uli.shared.api.problems import FieldError, ProblemException

CONTENT_AUTHOR = "content:author"
CONTENT_REVIEW = "content:review"
CONTENT_TAXONOMY_MANAGE = "content:taxonomy_manage"


def privileged_with(permission: str) -> Callable[..., Awaitable[AuthenticatedUser]]:
    allowed = require_permission(permission)

    async def dependency(
        user: Annotated[AuthenticatedUser, Depends(allowed)],
        _: Annotated[AuthenticatedUser, Depends(require_privileged)],
    ) -> AuthenticatedUser:
        return user

    return dependency


Author = Annotated[AuthenticatedUser, Depends(privileged_with(CONTENT_AUTHOR))]
Reviewer = Annotated[AuthenticatedUser, Depends(privileged_with(CONTENT_REVIEW))]
TaxonomyManager = Annotated[AuthenticatedUser, Depends(privileged_with(CONTENT_TAXONOMY_MANAGE))]


async def reject_unknown_query(request: Request) -> None:
    """Un parámetro de consulta que la ruta no declara es un error (422), no se ignora: así un
    filtro mal escrito no devuelve en silencio todo el banco."""
    route = request.scope.get("route")
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return
    declared = _query_names(dependant)
    unknown = sorted(set(request.query_params) - declared)
    if unknown:
        raise ProblemException(
            422,
            "validation-error",
            detail="Revisa los datos marcados.",
            errors=[FieldError(field=name, message="Parámetro desconocido.") for name in unknown],
        )


def _query_names(dependant: Dependant) -> set[str]:
    names = {param.alias for param in dependant.query_params}
    for sub in dependant.dependencies:
        names |= _query_names(sub)
    return names
