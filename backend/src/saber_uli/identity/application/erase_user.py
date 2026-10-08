"""Supresión de los datos personales de una solicitud (FR-033; research R-25; data-model §4.3).

Dos transacciones, para que el administrador vea la solicitud «En proceso» y el procesamiento
sea reanudable:

1. `received` → `in_progress`.
2. Borra lo que cuelga del usuario (perfil, membresías, sesiones, contacto de sus invitaciones),
   deja la lápida (sin nombre, correo, `oid` ni roles), publica `identity.UserErased`, completa
   la solicitud y audita `user.erased` y `deletion.completed`.

Si el worker cae entre ambas, la reanudación hace el paso 2 completo; si la lápida ya existía,
solo completa la solicitud. Una solicitud bloqueada por otro proceso se deja para después.
"""

from collections.abc import Callable
from uuid import UUID

import structlog

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.events import UserErased
from saber_uli.identity.domain.user import UserStatus
from saber_uli.shared.domain.clock import Clock

_log = structlog.get_logger(__name__)


class EraseUser:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, request_id: UUID) -> bool:
        """Devuelve `True` si completó la solicitud en esta llamada."""
        async with self._uow_factory() as uow:
            request = await uow.deletion_requests.get_for_update(request_id)
            if request is None or request.is_completed:
                return False
            request.start()
            await uow.deletion_requests.save(request)
            await uow.commit()

        now = self._clock.now()
        async with self._uow_factory() as uow:
            request = await uow.deletion_requests.get_for_update(request_id)
            if request is None or request.is_completed:
                return False
            user = await uow.users.get(request.user_id)
            if user is not None and user.status is not UserStatus.DELETED:
                await uow.erasure.erase(request.user_id)
                user.to_tombstone()
                await uow.users.save(user)
                uow.record(UserErased(user_id=request.user_id, occurred_at=now))
                await record_audit(
                    uow,
                    AuditAction.USER_ERASED,
                    target=AuditTarget.USER,
                    target_id=request.user_id,
                    subject_user_id=request.user_id,
                    now=now,
                )
            request.complete(now)
            await uow.deletion_requests.save(request)
            await record_audit(
                uow,
                AuditAction.DELETION_COMPLETED,
                target=AuditTarget.DELETION_REQUEST,
                target_id=request_id,
                subject_user_id=request.user_id,
                details={"origin": request.origin.value, "due_date": request.due_date.isoformat()},
                now=now,
            )
            await uow.commit()
        _log.info("deletion_completed", origin=request.origin.value)
        return True
