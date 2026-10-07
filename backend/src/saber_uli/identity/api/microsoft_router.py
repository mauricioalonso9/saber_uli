"""Ingreso con la cuenta institucional: `startMicrosoftLogin` y `completeMicrosoftLogin`.

FR-001 a FR-005, FR-036; research R-10 a R-13, R-31.

- `GET /api/auth/microsoft/login`: guarda `state`, `nonce`, el verificador PKCE y `return_to`
  (solo rutas internas) en la cookie firmada `su_oidc` (10 min, `/api/auth/microsoft`) y
  redirige a la autoridad del inquilino.
- `GET /api/auth/microsoft/callback`: valida `state` en tiempo constante y borra la cookie;
  canjea el código y valida el ID token; crea o actualiza la cuenta; abre la sesión (cookie
  `su_refresh`) y redirige al primer paso pendiente (`/bienvenida/datos`, `/bienvenida/perfil`)
  o a `return_to` (por defecto `/inicio`).
- Límite de 30/min por IP en `/login` (R-31).
- Cualquier rechazo redirige a `/ingresar?error=<código>` sin crear cuenta ni sesión y se
  registra `auth.login_rejected` con la causa, nunca el correo ni los tokens (FR-036).
"""

import hmac
import re
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from saber_uli.identity.api.auth_router import refresh_cookie
from saber_uli.identity.application.access_guard import AccountDeletedError, AccountDisabledError
from saber_uli.identity.application.authenticate_institutional_user import (
    AuthenticateInstitutionalUser,
    TenantNotAllowedError,
)
from saber_uli.identity.application.queries.consent_status import ConsentStatusQuery
from saber_uli.identity.application.sessions import SessionService
from saber_uli.identity.domain.session import AuthMethod
from saber_uli.identity.domain.user import User
from saber_uli.identity.infrastructure.entra_id import (
    EntraIdClient,
    IdpUnavailableError,
    LoginFailedError,
)
from saber_uli.shared.api.rate_limit import per_ip
from saber_uli.shared.infrastructure.rate_limit import AUTH_PER_IP

_log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/auth/microsoft", tags=["auth"])

PENDING_KEY = "oidc"
LOGIN_PATH = "/ingresar"
CONSENT_PATH = "/bienvenida/datos"
PROFILE_PATH = "/bienvenida/perfil"
HOME_PATH = "/inicio"
# Solo rutas internas: empiezan por "/" y no por "//" ni "/\" (evita redirecciones abiertas).
_SAFE_RETURN = re.compile(r"^/(?![/\\])[^\s]{0,199}$")


def _safe_return_to(value: str | None) -> str | None:
    return value if value and _SAFE_RETURN.fullmatch(value) else None


def _rejected(request: Request, code: str) -> RedirectResponse:
    request.session.clear()
    _log.info("auth.login_rejected", provider="entra_id", cause=code)
    return RedirectResponse(f"{LOGIN_PATH}?error={code}", status_code=302)


def _state(request: Request, name: str) -> Any:
    return getattr(request.app.state, name)


@router.get(
    "/login",
    operation_id="startMicrosoftLogin",
    status_code=302,
    dependencies=[Depends(per_ip(AUTH_PER_IP))],
)
async def start_microsoft_login(
    request: Request,
    # Un `return_to` inválido o externo se ignora (no es un error): se vuelve a /inicio.
    return_to: str | None = None,
) -> RedirectResponse:
    entra: EntraIdClient = _state(request, "entra_client")
    try:
        authorization = await entra.begin()
    except IdpUnavailableError:
        return _rejected(request, "idp_unavailable")
    except LoginFailedError:
        return _rejected(request, "login_failed")
    request.session[PENDING_KEY] = {
        "state": authorization.state,
        "nonce": authorization.nonce,
        "verifier": authorization.code_verifier,
        "return_to": _safe_return_to(return_to),
    }
    return RedirectResponse(authorization.url, status_code=302)


async def _next_step(request: Request, user: User, return_to: str | None) -> str:
    consents: ConsentStatusQuery = _state(request, "consent_checker")
    if user.id is not None and (await consents.status(user.id)).consent_required:
        return CONSENT_PATH
    if user.onboarding_completed_at is None:
        return PROFILE_PATH
    return return_to or HOME_PATH


# Sin límite propio: el callback solo avanza con la cookie firmada de un solo uso que emite
# `/login`, que sí está limitado (30/min por IP, R-31); el contrato no documenta 429 aquí.
@router.get("/callback", operation_id="completeMicrosoftLogin", status_code=302)
async def complete_microsoft_login(
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    pending = request.session.get(PENDING_KEY)
    # Todo error se expresa como redirección (el contrato solo documenta 302), también la
    # ausencia de `state`.
    if (
        not state
        or not isinstance(pending, dict)
        or not hmac.compare_digest(str(pending.get("state", "")), state)
    ):
        return _rejected(request, "invalid_state")
    request.session.clear()  # un solo uso: la cookie su_oidc se borra en la respuesta
    if error:
        return _rejected(request, "login_cancelled" if error == "access_denied" else "login_failed")
    if not code:
        return _rejected(request, "login_failed")

    entra: EntraIdClient = _state(request, "entra_client")
    authenticate: AuthenticateInstitutionalUser = _state(request, "authenticate_institutional")
    sessions: SessionService = _state(request, "session_service")
    try:
        claims = await entra.complete(
            code=code, code_verifier=pending["verifier"], nonce=pending["nonce"]
        )
        result = await authenticate.execute(claims)
    except TenantNotAllowedError:
        return _rejected(request, "tenant_not_allowed")
    except IdpUnavailableError:
        return _rejected(request, "idp_unavailable")
    except LoginFailedError:
        return _rejected(request, "login_failed")
    except AccountDisabledError:
        return _rejected(request, "account_disabled")
    except AccountDeletedError:
        return _rejected(request, "account_deleted")

    user = result.user
    if user.id is None:  # pragma: no cover - el caso de uso siempre guarda al usuario
        return _rejected(request, "login_failed")
    issued = await sessions.open_session(user.id, AuthMethod.ENTRA_ID)
    target = await _next_step(request, user, pending.get("return_to"))
    response = RedirectResponse(target, status_code=302)
    response.headers.append(
        "Set-Cookie", refresh_cookie(issued, sessions.seconds_until(issued.refresh_expires_at))
    )
    response.headers["Cache-Control"] = "no-store"
    _log.info(
        "auth.login_succeeded",
        provider="entra_id",
        user_id=str(user.id),
        first_login=result.created,
    )
    return response
