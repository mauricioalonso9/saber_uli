"""Rutas `/api/auth/refresh` y `/api/auth/logout` (contrato: `refreshSession`, `logout`).

La cookie `su_refresh` es `HttpOnly`, `Secure`, `SameSite=Strict` y `Path=/api/auth` (R-14).
Ambas rutas exigen `X-Requested-With: saber-uli`. Como el contrato no documenta un 4xx para su
ausencia, la renovación responde 401 `unauthenticated` y el cierre responde 204 sin revocar
nada (decisión pendiente registrada en tasks.md, T050).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from pydantic import BaseModel

from saber_uli.identity.application.sessions import IssuedSession, SessionService
from saber_uli.shared.api.problems import ProblemException
from saber_uli.shared.api.rate_limit import per_ip
from saber_uli.shared.domain.errors import UnauthenticatedError
from saber_uli.shared.infrastructure.rate_limit import AUTH_PER_IP

REFRESH_COOKIE = "su_refresh"
COOKIE_PATH = "/api/auth"
REQUESTED_WITH = "saber-uli"
_ATTRIBUTES = f"Path={COOKIE_PATH}; Secure; HttpOnly; SameSite=Strict"
DELETED_COOKIE = f"{REFRESH_COOKIE}=; Max-Age=0; {_ATTRIBUTES}"

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SessionTokens(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 - tipo de token, no un secreto
    expires_in: int


def _service(request: Request) -> SessionService:
    service: SessionService = request.app.state.session_service
    return service


def refresh_cookie(issued: IssuedSession, now_seconds_left: int) -> str:
    return f"{REFRESH_COOKIE}={issued.refresh_token}; Max-Age={now_seconds_left}; {_ATTRIBUTES}"


Service = Annotated[SessionService, Depends(_service)]
RequestedWith = Annotated[str | None, Header()]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post(
    "/refresh",
    operation_id="refreshSession",
    dependencies=[Depends(per_ip(AUTH_PER_IP))],
)
async def refresh_session(
    response: Response,
    service: Service,
    x_requested_with: RequestedWith = None,
    su_refresh: RefreshCookie = None,
) -> SessionTokens:
    if x_requested_with != REQUESTED_WITH:
        raise ProblemException(401, "unauthenticated", detail="Solicitud no válida.")
    if not su_refresh:
        raise ProblemException(
            401,
            "session-expired",
            detail="La sesión venció.",
            headers={"Set-Cookie": DELETED_COOKIE},
        )
    try:
        issued = await service.refresh(su_refresh)
    except UnauthenticatedError as error:
        raise ProblemException(
            401, error.slug, detail=error.message, headers={"Set-Cookie": DELETED_COOKIE}
        ) from None
    seconds_left = service.seconds_until(issued.refresh_expires_at)
    response.headers["Set-Cookie"] = refresh_cookie(issued, seconds_left)
    response.headers["Cache-Control"] = "no-store"
    return SessionTokens(access_token=issued.access_token, expires_in=issued.expires_in)


@router.post("/logout", operation_id="logout", status_code=204)
async def logout(
    service: Service,
    x_requested_with: RequestedWith = None,
    su_refresh: RefreshCookie = None,
) -> Response:
    if x_requested_with == REQUESTED_WITH and su_refresh:
        await service.logout(su_refresh)
    return Response(status_code=204, headers={"Set-Cookie": DELETED_COOKIE})
