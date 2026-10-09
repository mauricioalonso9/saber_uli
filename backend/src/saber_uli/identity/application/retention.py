"""Conservación automática de datos (FR-034a a FR-034d; research R-25).

`apply_retention` decide, con los datos vigentes y dentro de una transacción, qué toca hacer con
una cuenta:

- Aviso (30 días antes): marca `retention_notice_sent_at` y publica
  `identity.RetentionNoticeDue`; el worker envía el correo.
- Supresión (en la fecha): abre la solicitud con origen `guest_retention` o
  `institutional_retention`, como la solicitud voluntaria pero con actor sistema.
- El último administrador activo no se avisa ni se suprime: se audita
  `retention.skipped_last_admin` una vez por ciclo (desde su último ingreso).

Ingresar o renovar el acceso mueve las fechas: el cálculo siempre parte de los datos actuales.
"""

from datetime import datetime
from enum import StrEnum

from saber_uli.identity.application.admin_users import has_other_active_admin
from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.deletion import open_deletion
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.deletion_request import DeletionOrigin
from saber_uli.identity.domain.events import RetentionNoticeDue
from saber_uli.identity.domain.retention import (
    RetentionAction,
    RetentionSchedule,
    decide,
    guest_access_end,
    guest_schedule,
    institutional_schedule,
)
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import User, UserKind, UserStatus

_RETAINED = (UserStatus.ACTIVE, UserStatus.DISABLED)


class RetentionOutcome(StrEnum):
    NONE = "none"
    NOTICE_QUEUED = "notice_queued"
    DELETION_REQUESTED = "deletion_requested"
    SKIPPED_LAST_ADMIN = "skipped_last_admin"


async def schedule_for(
    uow: IdentityUnitOfWork, user: User, *, now: datetime
) -> RetentionSchedule | None:
    """Calendario vigente de la cuenta, o `None` si no aplica (invitado con acceso vigente o
    cuenta que ya está en supresión)."""
    if user.id is None or user.status not in _RETAINED:
        return None
    if user.kind is UserKind.INSTITUTIONAL:
        return institutional_schedule(user.last_login_at or user.created_at)
    invitation = await uow.invitations.latest_for_guest(user.id)
    if invitation is None or invitation.accepted_at is None:
        return None
    end = guest_access_end(
        access_expires_at=invitation.access_expires_at, revoked_at=invitation.revoked_at, now=now
    )
    return None if end is None else guest_schedule(end)


async def apply_retention(
    uow: IdentityUnitOfWork, user: User, *, now: datetime
) -> RetentionOutcome:
    """No confirma: quien llama hace `commit` si el resultado no es `NONE`."""
    schedule = await schedule_for(uow, user, now=now)
    if schedule is None or user.id is None:
        return RetentionOutcome.NONE
    action = decide(schedule, now=now, notice_sent_at=user.retention_notice_sent_at)
    if action is RetentionAction.NONE:
        return RetentionOutcome.NONE

    if (
        user.kind is UserKind.INSTITUTIONAL
        and user.is_active
        and Role.ADMIN in user.roles
        and not await has_other_active_admin(uow, user.id)
    ):
        if action is RetentionAction.ERASE and not await _skip_recorded(uow, user):
            await record_audit(
                uow,
                AuditAction.RETENTION_SKIPPED_LAST_ADMIN,
                target=AuditTarget.USER,
                target_id=user.id,
                subject_user_id=user.id,
                details={"erase_on": schedule.erase_on.isoformat()},
                now=now,
            )
            return RetentionOutcome.SKIPPED_LAST_ADMIN
        return RetentionOutcome.NONE

    if action is RetentionAction.SEND_NOTICE:
        user.retention_notice_sent_at = now
        await uow.users.save(user)
        uow.record(RetentionNoticeDue(user_id=user.id, occurred_at=now))
        return RetentionOutcome.NOTICE_QUEUED

    if await uow.deletion_requests.open_for_user(user.id) is not None:
        return RetentionOutcome.NONE
    origin = (
        DeletionOrigin.GUEST_RETENTION
        if user.kind is UserKind.GUEST
        else DeletionOrigin.INSTITUTIONAL_RETENTION
    )
    await open_deletion(uow, user, origin, now=now, actor_id=None)
    return RetentionOutcome.DELETION_REQUESTED


async def _skip_recorded(uow: IdentityUnitOfWork, user: User) -> bool:
    """¿Ya se auditó la omisión en este ciclo (desde el último ingreso)?"""
    _, total = await uow.audit.search(
        action=AuditAction.RETENTION_SKIPPED_LAST_ADMIN.value,
        actor_id=None,
        subject_user_id=user.id,
        since=user.last_login_at or user.created_at,
        until=None,
        offset=0,
        limit=1,
    )
    return total > 0
