"""Limitación de peticiones con `limits` y Redis (research R-31; principio IX).

Ventana deslizante con contador (evita las ráfagas en el borde de una ventana fija). La clave
por correo es un HMAC-SHA256 del correo normalizado: el correo nunca llega a Redis y no se puede
revertir con un diccionario sin la clave. Si Redis no responde se permite la petición y se
registra el hecho sin identificadores: la caída de Redis no debe tumbar la API (R-16).
"""

import hashlib
import hmac
import math
import time
from dataclasses import dataclass, field

import structlog
from limits import RateLimitItem, parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import SlidingWindowCounterRateLimiter

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    """Regla con nombre estable (parte de la clave en Redis) y límite en notación de `limits`."""

    name: str
    limit: str
    item: RateLimitItem = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "item", parse(self.limit))

    @property
    def window_seconds(self) -> int:
        return int(self.item.get_expiry())


# Ventanas de R-31.
GUEST_LINK_PER_EMAIL = RateLimitRule("guest-link-email", "5/hour")
GUEST_LINK_PER_IP = RateLimitRule("guest-link-ip", "20/hour")
GUEST_SESSION_PER_IP = RateLimitRule("guest-session-ip", "10/minute")
# Ingreso con Microsoft y renovación comparten el cupo por IP.
AUTH_PER_IP = RateLimitRule("auth-ip", "30/minute")
API_PER_USER = RateLimitRule("api-user", "300/minute")


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


def _async_uri(redis_url: str) -> str:
    for scheme in ("redis://", "rediss://"):
        if redis_url.startswith(scheme):
            return f"async+{redis_url}"
    raise ValueError("la URL de Redis debe empezar con redis:// o rediss://")


class RateLimiter:
    def __init__(
        self, redis_url: str, *, hash_key: bytes, key_prefix: str = "saber-uli:rl"
    ) -> None:
        if len(hash_key) < 32:
            raise ValueError("hash_key debe tener al menos 32 bytes")
        self._hash_key = hash_key
        storage = RedisStorage(
            _async_uri(redis_url),
            implementation="redispy",
            key_prefix=key_prefix,
            wrap_exceptions=True,
        )
        self._strategy = SlidingWindowCounterRateLimiter(storage)

    def email_key(self, email: str) -> str:
        normalized = email.strip().lower().encode()
        digest = hmac.new(self._hash_key, normalized, hashlib.sha256).hexdigest()
        return f"email:{digest}"

    async def hit(self, rule: RateLimitRule, key: str) -> RateLimitDecision:
        """Cuenta una petición; si excede la regla devuelve los segundos para reintentar."""
        try:
            if await self._strategy.hit(rule.item, rule.name, key):
                return RateLimitDecision(allowed=True)
            stats = await self._strategy.get_window_stats(rule.item, rule.name, key)
        except Exception as error:
            _log.warning("rate_limit_unavailable", rule=rule.name, error_type=type(error).__name__)
            return RateLimitDecision(allowed=True)
        wait = math.ceil(stats.reset_time - time.time())
        return RateLimitDecision(allowed=False, retry_after=min(max(wait, 1), rule.window_seconds))
