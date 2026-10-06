"""Guardia de acceso: valida el token de acceso y la época vigente del usuario (R-15, R-16).

En cada petición autenticada:

1. Se decodifica el token (firma, `kid`, vencimiento).
2. Se compara su `epoch` con el vigente: primero en la caché (Redis) y, si falta o Redis no
   responde, en la base de datos (se vuelve a guardar en la caché).
3. Si no coincide, se responde 401 con la causa: `account-disabled`, `account-deleted`,
   `guest-access-revoked`, `guest-access-expired` o, si nada de eso aplica (por ejemplo, se
   retiró un rol), `session-revoked`.

El vencimiento natural del acceso de invitado lo convierte en cambio de época la tarea
`expire_invitations` (T126); mientras tanto, la renovación (T050) lo comprueba, así que un token
de acceso de un invitado vencido dura como máximo sus 10 minutos.
"""

from collections.abc import Callable
from uuid import UUID

from saber_uli.identity.application.ports import (
    AccessTokenDecoder,
    EpochStore,
    GuestAccessStatus,
)
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.user import UserKind, UserStatus
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import UnauthenticatedError


class AccountDisabledError(UnauthenticatedError):
    slug = "account-disabled"


class AccountDeletedError(UnauthenticatedError):
    slug = "account-deleted"


class GuestAccessExpiredError(UnauthenticatedError):
    slug = "guest-access-expired"


class GuestAccessRevokedError(UnauthenticatedError):
    slug = "guest-access-revoked"


class SessionAccessRevokedError(UnauthenticatedError):
    slug = "session-revoked"


class AccessGuard:
    """Implementa `identity.application.public.Authenticator`."""

    def __init__(
        self,
        *,
        decoder: AccessTokenDecoder,
        epochs: EpochStore,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
    ) -> None:
        self._decoder = decoder
        self._epochs = epochs
        self._uow_factory = uow_factory
        self._clock = clock

    async def authenticate(self, token: str) -> AuthenticatedUser:
        claims = self._decoder.decode(token, now=self._clock.now())
        if await self._current_epoch(claims.sub) != claims.epoch:
            raise await self._denial(claims.sub)
        return AuthenticatedUser(
            id=claims.sub,
            session_id=claims.sid,
            roles=frozenset(claims.roles),
            privileged=claims.priv,
        )

    async def record_privileged_activity(self, user: AuthenticatedUser) -> None:
        async with self._uow_factory() as uow:
            session = await uow.sessions.get(user.session_id)
            if session is None:
                raise SessionAccessRevokedError("La sesión se cerró.")
            session.record_privileged_activity(self._clock.now())
            await uow.sessions.save(session)
            await uow.commit()

    async def _current_epoch(self, user_id: UUID) -> int | None:
        cached = await self._epochs.get(user_id)
        if cached is not None:
            return cached
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
        if user is None:
            return None
        await self._epochs.set(user_id, user.auth_epoch)
        return user.auth_epoch

    async def _denial(self, user_id: UUID) -> UnauthenticatedError:
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            guest_status = (
                await uow.guest_access.status_for(user_id, now=self._clock.now())
                if user is not None and user.kind is UserKind.GUEST
                else None
            )
        if user is None or user.status in (UserStatus.DELETED, UserStatus.DELETION_PENDING):
            return AccountDeletedError("Esta cuenta fue eliminada.")
        if user.status is UserStatus.DISABLED:
            return AccountDisabledError("La cuenta está desactivada.")
        if guest_status is GuestAccessStatus.REVOKED:
            return GuestAccessRevokedError("El acceso de invitado fue retirado.")
        if guest_status is GuestAccessStatus.EXPIRED:
            return GuestAccessExpiredError("El acceso de invitado venció.")
        return SessionAccessRevokedError("La sesión se cerró.")
