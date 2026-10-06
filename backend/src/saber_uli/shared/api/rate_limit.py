"""Dependencias de FastAPI para la limitación de peticiones (research R-31).

- `per_ip(regla)`: por la IP del cliente. Uvicorn la toma de `X-Forwarded-For`, que Nginx
  sobrescribe con la IP real (`--proxy-headers`), así que el cliente no puede falsificarla.
- `per_user(regla, dependencia_de_usuario)`: por usuario autenticado (T048 aporta
  `current_user`).
- `RateLimitGuard.check_email(regla, correo)`: para límites que dependen del cuerpo; el handler
  la llama tras validar la petición.

El limitador vive en `app.state.rate_limiter` (lo crea `main.py`, T058). Al exceder un límite
se responde 429 `rate-limited` con `Retry-After`.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends, Request

from saber_uli.shared.api.problems import ProblemException
from saber_uli.shared.infrastructure.rate_limit import RateLimiter, RateLimitRule

RATE_LIMITED_DETAIL = "Hiciste demasiadas solicitudes seguidas. Espera un momento."


class RateLimitGuard:
    def __init__(self, limiter: RateLimiter) -> None:
        self._limiter = limiter

    async def check(self, rule: RateLimitRule, key: str) -> None:
        decision = await self._limiter.hit(rule, key)
        if not decision.allowed:
            raise ProblemException(
                429,
                "rate-limited",
                detail=RATE_LIMITED_DETAIL,
                headers={"Retry-After": str(decision.retry_after)},
            )

    async def check_email(self, rule: RateLimitRule, email: str) -> None:
        await self.check(rule, self._limiter.email_key(email))


def rate_limit_guard(request: Request) -> RateLimitGuard:
    limiter: RateLimiter = request.app.state.rate_limiter
    return RateLimitGuard(limiter)


Guard = Annotated[RateLimitGuard, Depends(rate_limit_guard)]


def per_ip(rule: RateLimitRule) -> Callable[..., Awaitable[None]]:
    async def dependency(request: Request, guard: Guard) -> None:
        ip = request.client.host if request.client else "unknown"
        await guard.check(rule, f"ip:{ip}")

    return dependency


def per_user(
    rule: RateLimitRule, user_dependency: Callable[..., Any]
) -> Callable[..., Awaitable[None]]:
    async def dependency(guard: Guard, user: Annotated[Any, Depends(user_dependency)]) -> None:
        user_id = getattr(user, "id", user)
        await guard.check(rule, f"user:{user_id}")

    return dependency
