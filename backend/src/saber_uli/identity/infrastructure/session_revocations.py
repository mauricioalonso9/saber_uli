"""Lista de sesiones revocadas en Redis (ASVS 4.0.3 V3.3.1; revisión T070).

Al cerrar sesión o revocarla por reutilización del token de renovación, el `sid` entra en esta
lista durante la vida máxima de un token de acceso (más un margen). Así el token de acceso ya
emitido deja de servir de inmediato, sin esperar sus 10 minutos. Si Redis no responde, la
consulta se comporta como "no revocada" y se registra (coherente con R-16).
"""

from uuid import UUID

import structlog
from redis.asyncio import Redis

from saber_uli.identity.application.ports import ACCESS_TOKEN_TTL_SECONDS

_log = structlog.get_logger(__name__)

KEY_PREFIX = "saber-uli:revoked-session:"
TTL_SECONDS = ACCESS_TOKEN_TTL_SECONDS + 60


class RedisSessionRevocations:
    def __init__(self, redis_url: str, *, ttl_seconds: int = TTL_SECONDS) -> None:
        self._redis = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
        self._ttl = ttl_seconds

    async def revoke(self, session_id: UUID) -> None:
        try:
            await self._redis.set(f"{KEY_PREFIX}{session_id}", 1, ex=self._ttl)
        except Exception as error:
            _log.warning(
                "session_revocation_unavailable",
                operation="revoke",
                error_type=type(error).__name__,
            )

    async def is_revoked(self, session_id: UUID) -> bool:
        try:
            return bool(await self._redis.exists(f"{KEY_PREFIX}{session_id}"))
        except Exception as error:
            _log.warning(
                "session_revocation_unavailable",
                operation="is_revoked",
                error_type=type(error).__name__,
            )
            return False

    async def close(self) -> None:
        await self._redis.aclose()
