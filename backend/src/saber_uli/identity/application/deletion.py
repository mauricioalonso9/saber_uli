"""Solicitudes de supresión (FR-032, FR-034, FR-034d; research R-25; data-model §4.1).

Al solicitarla, la cuenta pasa a `deletion_pending`: `auth_epoch` + 1 y se revocan sus
sesiones, así la siguiente petición responde 401. La fecha límite es de 15 días hábiles; el
worker la procesa de inmediato por el outbox (`identity.DeletionRequested`) y, como respaldo,
cada 15 minutos.

El último administrador activo no puede solicitarla hasta que otra persona tenga el rol
(FR-034d), con el mismo bloqueo de FR-025.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from saber_uli.identity.application.admin_users import ensure_other_admin
from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.deletion_request import (
    DeletionAlreadyRequestedError,
    DeletionOrigin,
    DeletionRequest,
    DeletionStatus,
)
from saber_uli.identity.domain.events import DeletionRequested, UserAccessChanged
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import User
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import NotFoundError, UnauthenticatedError

__all__ = [
    "DeletionAlreadyRequestedError",
    "DeletionRequestNotFoundError",
    "DeletionService",
    "open_deletion",
]


class DeletionRequestNotFoundError(NotFoundError):
    slug = "not-found"


class DeletionService:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def request(self, user_id: UUID) -> DeletionRequest:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            if user is None:
                raise UnauthenticatedError("La sesión no es válida.")
            if await uow.deletion_requests.open_for_user(user_id) is not None:
                raise DeletionAlreadyRequestedError("Ya hay una solicitud de supresión en curso.")
            if Role.ADMIN in user.roles and user.is_active:
                await ensure_other_admin(
                    uow,
                    user_id,
                    message=(
                        "Eres el último administrador activo: asigna el rol Administrador a otra "
                        "persona antes de eliminar tu cuenta."
                    ),
                )
            request = await open_deletion(
                uow, user, DeletionOrigin.USER_REQUEST, now=now, actor_id=user_id
            )
            await uow.commit()
        return request

    async def mine(self, user_id: UUID) -> DeletionRequest:
        async with self._uow_factory() as uow:
            request = await uow.deletion_requests.open_for_user(user_id)
        if request is None:
            raise DeletionRequestNotFoundError("No tienes una solicitud de supresión en curso.")
        return request

    async def list(
        self, *, status: DeletionStatus | None, offset: int, limit: int
    ) -> tuple[list[DeletionRequest], int]:
        async with self._uow_factory() as uow:
            return await uow.deletion_requests.search(status=status, offset=offset, limit=limit)


async def open_deletion(
    uow: IdentityUnitOfWork,
    user: User,
    origin: DeletionOrigin,
    *,
    now: datetime,
    actor_id: UUID | None,
) -> DeletionRequest:
    """Abre la solicitud y termina el acceso; la usan la solicitud voluntaria y la tarea de
    conservación (`actor_id = None`: el sistema)."""
    if user.id is None:
        raise ValueError("el usuario no está guardado")
    user.request_deletion()
    await uow.users.save(user)
    request = await uow.deletion_requests.add(DeletionRequest.open(user.id, origin, now=now))
    if request.id is None:
        raise ValueError("la solicitud no quedó guardada")
    await uow.sessions.revoke_all_for_user(user.id, now=now, reason="access_changed")
    uow.record(UserAccessChanged(user_id=user.id, occurred_at=now))
    uow.record(DeletionRequested(user_id=user.id, deletion_request_id=request.id, occurred_at=now))
    await record_audit(
        uow,
        AuditAction.DELETION_REQUESTED,
        target=AuditTarget.DELETION_REQUEST,
        target_id=request.id,
        subject_user_id=user.id,
        actor_id=actor_id,
        details={"origin": origin.value, "due_date": request.due_date.isoformat()},
        now=now,
    )
    return request
