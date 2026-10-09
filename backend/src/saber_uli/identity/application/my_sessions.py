"""Sesiones activas del usuario (FR-037a, escenario 1.5; ASVS 4.0.3 V3.3.4; T178b).

Se listan las sesiones en uso (sin revocar, antes de su vencimiento absoluto y con actividad en
los últimos 7 días; data-model §2.13), sin IP ni datos del dispositivo. Cerrar una la revoca
(`user_revoked`) y pone su `id` en la lista de sesiones revocadas: su token de acceso ya emitido
deja de servir en la siguiente petición y su token de renovación ya no rota, como al cerrar
sesión.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saber_uli.identity.application.ports import SessionRevocations
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.session import AuthMethod
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import NotFoundError


class SessionNotFoundError(NotFoundError):
    """La sesión no existe, es de otra persona o ya no está en uso (404, sin distinguir)."""

    slug = "not-found"


@dataclass(frozen=True)
class ActiveSession:
    id: UUID
    auth_method: AuthMethod
    started_at: datetime
    last_activity_at: datetime
    current: bool


class MySessions:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        revocations: SessionRevocations,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._revocations = revocations

    async def list(self, user_id: UUID, *, current: UUID) -> list[ActiveSession]:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            sessions = await uow.sessions.list_for_user(user_id)
        return [
            ActiveSession(
                id=session.id,
                auth_method=session.auth_method,
                started_at=session.auth_time,
                last_activity_at=session.last_seen_at,
                current=session.id == current,
            )
            for session in sessions
            if session.id is not None and session.is_in_use(now)
        ]

    async def revoke(self, user_id: UUID, session_id: UUID) -> None:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            session = await uow.sessions.get(session_id)
            if session is None or session.user_id != user_id or not session.is_in_use(now):
                raise SessionNotFoundError("La sesión no existe o ya está cerrada.")
            session.revoke(now, "user_revoked")
            await uow.sessions.save(session)
            await uow.commit()
        await self._revocations.revoke(session_id)

    async def revoke_others(self, user_id: UUID, *, current: UUID) -> None:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            closed = [
                session
                for session in await uow.sessions.list_for_user(user_id)
                if session.id != current and session.is_active(now)
            ]
            for session in closed:
                session.revoke(now, "user_revoked")
                await uow.sessions.save(session)
            await uow.commit()
        for session in closed:
            if session.id is not None:
                await self._revocations.revoke(session.id)
