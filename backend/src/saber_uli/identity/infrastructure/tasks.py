"""Tareas periódicas de `identity` que ejecuta el worker (data-model §2.7, §2.9 y §4.2).

`expire_invitations` (cada hora, idempotente):

1. `sent` cuyo enlace o cuyo acceso venció → `expired` (se reenvía o se renueva desde la
   gestión de invitaciones).
2. `accepted` con el acceso vencido → `expired`; el invitado recibe `auth_epoch` + 1 y sus
   sesiones se revocan (FR-011). Sin esto, un token de acceso ya emitido valdría hasta 10 min.
3. FR-034e: una invitación nunca aceptada pierde correo y nombre, y se borran sus enlaces, 90
   días después de su revocación o, si no fue revocada, del vencimiento de su enlace.
4. Los lotes pendientes que pasaron sus 24 horas quedan `expired`, y los lotes confirmados o
   vencidos hace más de 30 días se borran (contienen correos).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import delete, or_, select, update

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.domain.events import UserAccessChanged
from saber_uli.identity.domain.invitation import InvitationStatus
from saber_uli.identity.infrastructure.orm import (
    AccessLinkRow,
    InvitationBatchRow,
    InvitationRow,
)
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.domain.clock import Clock

_log = structlog.get_logger(__name__)

CONTACT_RETENTION = timedelta(days=90)
BATCH_RETENTION = timedelta(days=30)


@dataclass(frozen=True)
class ExpirationReport:
    expired_pending: int
    expired_access: int
    purged_contacts: int


async def expire_invitations(
    *, uow_factory: Callable[[], SqlAlchemyIdentityUnitOfWork], clock: Clock
) -> ExpirationReport:
    now = clock.now()
    async with uow_factory() as uow:
        db = uow.session

        pending = await db.execute(
            update(InvitationRow)
            .where(InvitationRow.status == InvitationStatus.SENT.value)
            .where(
                or_(InvitationRow.link_expires_at <= now, InvitationRow.access_expires_at <= now)
            )
            .values(status=InvitationStatus.EXPIRED.value, updated_at=now)
        )

        ended = list(
            (
                await db.execute(
                    select(InvitationRow.id, InvitationRow.guest_user_id)
                    .where(InvitationRow.status == InvitationStatus.ACCEPTED.value)
                    .where(InvitationRow.access_expires_at <= now)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for invitation_id, guest_user_id in ended:
            await db.execute(
                update(InvitationRow)
                .where(InvitationRow.id == invitation_id)
                .values(status=InvitationStatus.EXPIRED.value, updated_at=now)
            )
            if guest_user_id is not None:
                await _end_guest_sessions(uow, guest_user_id, now=now)

        purge_ids = list(
            (
                await db.scalars(
                    select(InvitationRow.id)
                    .where(InvitationRow.accepted_at.is_(None))
                    .where(InvitationRow.email.is_not(None))
                    .where(
                        or_(
                            InvitationRow.revoked_at <= now - CONTACT_RETENTION,
                            (InvitationRow.revoked_at.is_(None))
                            & (InvitationRow.link_expires_at <= now - CONTACT_RETENTION),
                        )
                    )
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        if purge_ids:
            await db.execute(
                update(InvitationRow)
                .where(InvitationRow.id.in_(purge_ids))
                .values(email=None, invitee_name=None, updated_at=now)
            )
            await db.execute(
                delete(AccessLinkRow).where(AccessLinkRow.invitation_id.in_(purge_ids))
            )
            for invitation_id in purge_ids:
                await record_audit(
                    uow,
                    AuditAction.INVITATION_CONTACT_PURGED,
                    target=AuditTarget.INVITATION,
                    target_id=invitation_id,
                    now=now,
                )

        await db.execute(
            update(InvitationBatchRow)
            .where(InvitationBatchRow.status == "pending_confirmation")
            .where(InvitationBatchRow.expires_at <= now)
            .values(status="expired")
        )
        await db.execute(
            delete(InvitationBatchRow)
            .where(InvitationBatchRow.status.in_(("confirmed", "expired")))
            .where(
                or_(
                    InvitationBatchRow.confirmed_at <= now - BATCH_RETENTION,
                    InvitationBatchRow.expires_at <= now - BATCH_RETENTION,
                )
            )
        )
        await uow.commit()

    report = ExpirationReport(
        expired_pending=pending.rowcount or 0,  # type: ignore[attr-defined]
        expired_access=len(ended),
        purged_contacts=len(purge_ids),
    )
    _log.info(
        "invitations_expired",
        expired_pending=report.expired_pending,
        expired_access=report.expired_access,
        purged_contacts=report.purged_contacts,
    )
    return report


async def _end_guest_sessions(
    uow: SqlAlchemyIdentityUnitOfWork, guest_user_id: UUID, *, now: datetime
) -> None:
    guest = await uow.users.get(guest_user_id)
    if guest is None:
        return
    guest.invalidate_sessions()
    await uow.users.save(guest)
    await uow.sessions.revoke_all_for_user(guest_user_id, now=now, reason="access_changed")
    uow.record(UserAccessChanged(user_id=guest_user_id, occurred_at=now))
