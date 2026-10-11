"""Cuenta local de administración (contrato: `createLocalSession`, `changeLocalPassword`;
US9, FR-040 a FR-047; R-41; ADR 0009).

- `POST /api/auth/local/sessions`: usuario y contraseña. Credenciales incorrectas o cuenta no
  activa: 401 `invalid-credentials`, siempre el mismo mensaje; cuenta bloqueada: 429
  `account-locked` con `Retry-After`. 30/min por IP.
- `POST /api/auth/local/password`: con la sesión de la cuenta (también la restringida por el
  cambio pendiente), cambia la contraseña y devuelve una sesión nueva.

Los registros llevan la causa, nunca el usuario escrito ni la contraseña.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.identity.api.auth_router import SessionTokens, refresh_cookie
from saber_uli.identity.application.local_sign_in import AccountLockedError, LocalSignIn
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.sessions import IssuedSession, SessionService
from saber_uli.shared.api.auth import current_user
from saber_uli.shared.api.problems import ProblemException
from saber_uli.shared.api.rate_limit import per_ip
from saber_uli.shared.domain.errors import DomainError
from saber_uli.shared.infrastructure.rate_limit import (
    LOCAL_PASSWORD_PER_IP,
    LOCAL_SESSION_PER_IP,
)

router = APIRouter(prefix="/api/auth/local", tags=["auth"])
_log = structlog.get_logger(__name__)


class LocalSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, Field(min_length=1, max_length=64)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class PasswordChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Annotated[str, Field(min_length=1, max_length=128)]


def _service(request: Request) -> LocalSignIn:
    service: LocalSignIn = request.app.state.local_sign_in
    return service


def _sessions(request: Request) -> SessionService:
    service: SessionService = request.app.state.session_service
    return service


def _tokens(
    request: Request, response: Response, sessions: SessionService, issued: IssuedSession
) -> SessionTokens:
    response.headers["Set-Cookie"] = refresh_cookie(
        request, issued, sessions.seconds_until(issued.refresh_expires_at)
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionTokens(access_token=issued.access_token, expires_in=issued.expires_in)


@router.post(
    "/sessions",
    operation_id="createLocalSession",
    dependencies=[Depends(per_ip(LOCAL_SESSION_PER_IP))],
)
async def create_local_session(
    request: Request,
    body: LocalSessionIn,
    response: Response,
    service: Annotated[LocalSignIn, Depends(_service)],
    sessions: Annotated[SessionService, Depends(_sessions)],
) -> SessionTokens:
    try:
        issued = await service.sign_in(body.username, body.password)
    except AccountLockedError as error:
        _log.info("auth.login_rejected", provider="local_password", cause=error.slug)
        raise ProblemException(
            429,
            error.slug,
            detail=error.message,
            headers={"Retry-After": str(max(1, error.seconds))},
        ) from error
    except DomainError as error:
        _log.info("auth.login_rejected", provider="local_password", cause=error.slug)
        raise
    _log.info("auth.login_succeeded", provider="local_password")
    return _tokens(request, response, sessions, issued)


@router.post(
    "/password",
    operation_id="changeLocalPassword",
    dependencies=[Depends(per_ip(LOCAL_PASSWORD_PER_IP))],
)
async def change_local_password(
    request: Request,
    body: PasswordChangeIn,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
    service: Annotated[LocalSignIn, Depends(_service)],
    sessions: Annotated[SessionService, Depends(_sessions)],
) -> SessionTokens:
    issued = await service.change_password(user.id, body.current_password, body.new_password)
    _log.info("auth.password_changed", provider="local_password")
    return _tokens(request, response, sessions, issued)
