"""Caché de `auth_epoch` en Redis (research R-16).

Cada entrada vence a los 5 minutos: si una invalidación se pierde, la época vieja no dura más
que eso. Si Redis no responde, la caché se comporta como vacía (la época se lee de la base de
datos) y se registra el hecho sin identificadores.
"""

from uuid import UUID

import structlog
from redis.asyncio import Redis

_log = structlog.get_logger(__name__)

KEY_PREFIX = "saber-uli:auth-epoch:"
TTL_SECONDS = 300


class RedisEpochStore:
    def __init__(self, redis_url: str, *, ttl_seconds: int = TTL_SECONDS) -> None:
        self._redis = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
        self._ttl = ttl_seconds

    @staticmethod
    def _key(user_id: UUID) -> str:
        return f"{KEY_PREFIX}{user_id}"

    async def get(self, user_id: UUID) -> int | None:
        try:
            value = await self._redis.get(self._key(user_id))
        except Exception as error:
            _log.warning(
                "epoch_cache_unavailable", operation="get", error_type=type(error).__name__
            )
            return None
        return int(value) if value is not None else None

    async def set(self, user_id: UUID, epoch: int) -> None:
        try:
            await self._redis.set(self._key(user_id), epoch, ex=self._ttl)
        except Exception as error:
            _log.warning(
                "epoch_cache_unavailable", operation="set", error_type=type(error).__name__
            )

    async def invalidate(self, user_id: UUID) -> None:
        try:
            await self._redis.delete(self._key(user_id))
        except Exception as error:
            _log.warning(
                "epoch_cache_unavailable", operation="invalidate", error_type=type(error).__name__
            )

    async def close(self) -> None:
        await self._redis.aclose()
