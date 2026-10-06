"""Guardia de autorización de datos para `/api/v1` (FR-014).

Toda ruta de `/api/v1` exige una autorización de datos vigente, salvo:

- las marcadas `x-consent-exempt` en el contrato (consultar y decidir la autorización, `/me` y
  la supresión), que sí exigen sesión;
- las públicas (`security: []`), que no exigen sesión.

Las listas copian el contrato; una prueba (T051) verifica que coincidan. El contrato no viaja en
la imagen Docker, por eso no se lee en tiempo de ejecución. Se aplica como dependencia del router
de `/api/v1` (T058).
"""

from typing import Annotated

from fastapi import Depends, Header, Request

from saber_uli.identity.application.public import Authenticator, ConsentChecker
from saber_uli.shared.api.auth import current_user
from saber_uli.shared.api.problems import ProblemException

CONSENT_EXEMPT_OPERATIONS = frozenset(
    {
        "getMe",
        "listMyConsents",
        "decideConsent",
        "revokeConsent",
        "getMyDeletionRequest",
        "requestMyDeletion",
    }
)
PUBLIC_OPERATIONS = frozenset({"getCurrentPolicy", "getPolicyVersion"})


def _operation_id(request: Request) -> str | None:
    route = request.scope.get("route")
    operation_id = getattr(route, "operation_id", None)
    return operation_id if isinstance(operation_id, str) else None


async def require_consent(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> None:
    operation_id = _operation_id(request)
    if operation_id in PUBLIC_OPERATIONS:
        return
    authenticator: Authenticator = request.app.state.authenticator
    user = await current_user(authenticator, authorization)
    if operation_id in CONSENT_EXEMPT_OPERATIONS:
        return
    checker: ConsentChecker = request.app.state.consent_checker
    if not await checker.has_current_consent(user.id):
        raise ProblemException(
            403,
            "consent-required",
            detail="Para continuar debes aceptar la política de tratamiento de datos vigente.",
        )


ConsentGuard = Annotated[None, Depends(require_consent)]
