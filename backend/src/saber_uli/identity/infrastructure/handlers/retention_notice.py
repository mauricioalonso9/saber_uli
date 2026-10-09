"""Aviso de supresión automática en 30 días (FR-034c; research R-25).

Al procesar `identity.RetentionNoticeDue`, el manejador vuelve a calcular el calendario con los
datos actuales. Si la persona ingresó o renovó su acceso desde que se encoló el aviso
(`retention_notice_sent_at` ya no está o la fecha cambió), no envía nada. Si envía, audita
`retention.notice_sent`.

Si el correo falla, la excepción llega al despachador, que reintenta; la supresión no depende
del aviso y sigue en la fecha prevista.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

import structlog

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.retention import schedule_for
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.user import UserKind
from saber_uli.identity.infrastructure.handlers.link_emails import long_date
from saber_uli.notifications.application.public import EmailService
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.infrastructure.outbox import OutboxMessage, OutboxRegistry

_log = structlog.get_logger(__name__)

_TEMPLATES = {
    UserKind.GUEST: "retention_notice_guest",
    UserKind.INSTITUTIONAL: "retention_notice_institutional",
}


class RetentionNoticeHandler:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        email: EmailService,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._email = email
        self._clock = clock

    def register(self, registry: OutboxRegistry) -> None:
        registry.register("identity.RetentionNoticeDue", self.on_notice_due)

    async def on_notice_due(self, message: OutboxMessage) -> None:
        user_id = UUID(str(message.payload["user_id"]))
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            schedule = None if user is None else await schedule_for(uow, user, now=now)
            if (
                user is None
                or schedule is None
                or user.email is None
                or user.retention_notice_sent_at is None
                or user.retention_notice_sent_at < schedule.notice_at
            ):
                _log.info("retention_notice_skipped")
                return
            context: dict[str, Any] = {
                "name": user.display_name,
                "erase_on": long_date(schedule.erase_at),
            }
            if user.kind is UserKind.GUEST:
                invitation = await uow.invitations.latest_for_guest(user_id)
                inviter = invitation.invited_by if invitation else None
                names = await uow.users.display_names([inviter]) if inviter else {}
                context["inviter_name"] = names.get(inviter) if inviter else None
            else:
                context["sign_in_path"] = "/ingresar"
            to, kind = user.email, user.kind

        await self._email.send_email(_TEMPLATES[kind], to, context)

        async with self._uow_factory() as uow:
            await record_audit(
                uow,
                AuditAction.RETENTION_NOTICE_SENT,
                target=AuditTarget.USER,
                target_id=user_id,
                subject_user_id=user_id,
                details={"kind": kind.value, "erase_on": schedule.erase_on.isoformat()},
                now=now,
            )
            await uow.commit()
