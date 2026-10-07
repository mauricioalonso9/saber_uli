"""Ingreso de invitados (contrato: `createGuestSession`, `requestGuestSignInLink`; R-18, R-31).

- `POST /api/auth/guest/sessions`: consume el enlace del correo y abre la sesión (cookie
  `su_refresh`, como el ingreso institucional). Enlace inválido, usado o vencido → 400
  `access-link-invalid`; acceso vencido o revocado → 403 con la causa. 10/min por IP.
- `POST /api/auth/guest/link-requests`: siempre 202 con el mismo cuerpo (FR-013). 5/h por correo
  (solo su HMAC llega a Redis) y 20/h por IP.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.identity.api.auth_router import SessionTokens, refresh_cookie
from saber_uli.identity.application.guest_sessions import GuestSignIn, RequestSignInLink
from saber_uli.identity.application.sessions import SessionService
from saber_uli.identity.domain.invitation import GuestAccessExpiredError, GuestAccessRevokedError
from saber_uli.shared.api.problems import ProblemException
from saber_uli.shared.api.rate_limit import Guard, per_ip
from saber_uli.shared.infrastructure.rate_limit import (
    GUEST_LINK_PER_EMAIL,
    GUEST_LINK_PER_IP,
    GUEST_SESSION_PER_IP,
)

router = APIRouter(prefix="/api/auth/guest", tags=["auth"])

LINK_REQUEST_MESSAGE = (
    "Si el correo corresponde a un invitado con acceso vigente, en unos minutos recibirá un "
    "enlace para ingresar."
)


class GuestSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: Annotated[str, Field(min_length=32, max_length=128)]


class LinkRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Annotated[str, Field(max_length=254, pattern=r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")]


class Accepted(BaseModel):
    message: str


def _sign_in(request: Request) -> GuestSignIn:
    service: GuestSignIn = request.app.state.guest_sign_in
    return service


def _link_requests(request: Request) -> RequestSignInLink:
    service: RequestSignInLink = request.app.state.request_sign_in_link
    return service


def _sessions(request: Request) -> SessionService:
    service: SessionService = request.app.state.session_service
    return service


@router.post(
    "/sessions",
    operation_id="createGuestSession",
    dependencies=[Depends(per_ip(GUEST_SESSION_PER_IP))],
)
async def create_guest_session(
    body: GuestSessionIn,
    response: Response,
    service: Annotated[GuestSignIn, Depends(_sign_in)],
    sessions: Annotated[SessionService, Depends(_sessions)],
) -> SessionTokens:
    try:
        issued = await service.execute(body.token)
    except (GuestAccessExpiredError, GuestAccessRevokedError) as error:
        # En la renovación estas causas son 401; aquí la persona aún no tiene sesión: 403.
        raise ProblemException(403, error.slug, detail=error.message) from error
    response.headers["Set-Cookie"] = refresh_cookie(
        issued, sessions.seconds_until(issued.refresh_expires_at)
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionTokens(access_token=issued.access_token, expires_in=issued.expires_in)


@router.post(
    "/link-requests",
    operation_id="requestGuestSignInLink",
    status_code=202,
    dependencies=[Depends(per_ip(GUEST_LINK_PER_IP))],
)
async def request_guest_sign_in_link(
    body: LinkRequestIn,
    guard: Guard,
    service: Annotated[RequestSignInLink, Depends(_link_requests)],
) -> Accepted:
    await guard.check_email(GUEST_LINK_PER_EMAIL, body.email.strip().lower())
    await service.execute(body.email)
    return Accepted(message=LINK_REQUEST_MESSAGE)
