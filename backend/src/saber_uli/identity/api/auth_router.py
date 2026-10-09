"""Rutas `/api/auth/refresh` y `/api/auth/logout` (contrato: `refreshSession`, `logout`).

La cookie `su_refresh` es `HttpOnly`, `Secure`, `SameSite=Strict` y `Path=/api/auth` (R-14); sin
`Secure` solo cuando `PUBLIC_BASE_URL` es http, lo que la configuración admite únicamente en
localhost. Ambas rutas exigen `X-Requested-With: saber-uli` y la cookie (`security:
refreshCookie` en el contrato). Si falta alguna responden 401 `unauthenticated` y borran la
cookie.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from pydantic import BaseModel

from saber_uli.identity.application.sessions import IssuedSession, SessionService
from saber_uli.shared.api.problems import ProblemException
from saber_uli.shared.api.rate_limit import RateLimitGuard, per_ip, rate_limit_guard
from saber_uli.shared.domain.errors import UnauthenticatedError
from saber_uli.shared.infrastructure.rate_limit import REFRESH_PER_IP, REFRESH_PER_SESSION

REFRESH_COOKIE = "su_refresh"
COOKIE_PATH = "/api/auth"
REQUESTED_WITH = "saber-uli"

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SessionTokens(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 - tipo de token, no un secreto
    expires_in: int


def _service(request: Request) -> SessionService:
    service: SessionService = request.app.state.session_service
    return service


def cookie_is_secure(request: Request) -> bool:
    """`Secure` salvo cuando `PUBLIC_BASE_URL` es http (solo se admite en localhost, para
    desarrollo y e2e): WebKit no guarda cookies `Secure` en http://localhost."""
    settings = getattr(request.app.state, "settings", None)
    return settings is None or str(settings.public_base_url).startswith("https://")


def _attributes(request: Request) -> str:
    secure = " Secure;" if cookie_is_secure(request) else ""
    return f"Path={COOKIE_PATH};{secure} HttpOnly; SameSite=Strict"


def refresh_cookie(request: Request, issued: IssuedSession, seconds_left: int) -> str:
    return (
        f"{REFRESH_COOKIE}={issued.refresh_token}; Max-Age={seconds_left}; {_attributes(request)}"
    )


def deleted_cookie(request: Request) -> str:
    return f"{REFRESH_COOKIE}=; Max-Age=0; {_attributes(request)}"


Service = Annotated[SessionService, Depends(_service)]
RequestedWith = Annotated[str | None, Header()]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post(
    "/refresh",
    operation_id="refreshSession",
    dependencies=[Depends(per_ip(REFRESH_PER_IP))],
)
async def refresh_session(
    request: Request,
    response: Response,
    service: Service,
    guard: Annotated[RateLimitGuard, Depends(rate_limit_guard)],
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
            headers={"Set-Cookie": deleted_cookie(request)},
        )
    await guard.check_opaque(REFRESH_PER_SESSION, su_refresh)
    try:
        issued = await service.refresh(su_refresh)
    except UnauthenticatedError as error:
        raise ProblemException(
            401, error.slug, detail=error.message, headers={"Set-Cookie": deleted_cookie(request)}
        ) from None
    seconds_left = service.seconds_until(issued.refresh_expires_at)
    response.headers["Set-Cookie"] = refresh_cookie(request, issued, seconds_left)
    response.headers["Cache-Control"] = "no-store"
    return SessionTokens(access_token=issued.access_token, expires_in=issued.expires_in)


@router.post("/logout", operation_id="logout", status_code=204)
async def logout(
    request: Request,
    service: Service,
    x_requested_with: RequestedWith = None,
    su_refresh: RefreshCookie = None,
) -> Response:
    if x_requested_with != REQUESTED_WITH or not su_refresh:
        raise ProblemException(
            401,
            "unauthenticated",
            detail="No hay una sesión que cerrar.",
            headers={"Set-Cookie": deleted_cookie(request)},
        )
    await service.logout(su_refresh)
    return Response(status_code=204, headers={"Set-Cookie": deleted_cookie(request)})
