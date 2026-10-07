"""Crear invitaciones (FR-006, FR-008; research R-19, R-20).

Creación mínima para el comando `invite-guest` (T118); la gestión completa (docentes, lotes,
reenvío, revocación) llega con US5. El correo con el enlace lo envía el worker al procesar
`InvitationCreated`: aquí no se genera ningún token.
"""

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.events import InvitationCreated
from saber_uli.identity.domain.invitation import (
    InstitutionalEmailNotInvitableError,
    Invitation,
    InvitationAlreadyActiveError,
    is_institutional_email,
)
from saber_uli.shared.domain.clock import Clock


class CreateInvitation:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        institutional_domains: Sequence[str],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._domains = tuple(institutional_domains)

    async def execute(
        self,
        *,
        email: str,
        invited_by: UUID | None,
        access_expires_at: datetime | None = None,
        access_days: int | None = None,
        invitee_name: str | None = None,
    ) -> Invitation:
        """Sin `access_expires_at` ni `access_days`, usa el plazo por defecto de los parámetros."""
        if is_institutional_email(email, self._domains):
            raise InstitutionalEmailNotInvitableError(
                "Las personas con correo institucional ingresan con su cuenta Unilibre."
            )
        now = self._clock.now()
        async with self._uow_factory() as uow:
            if await uow.invitations.find_active_by_email(email) is not None:
                raise InvitationAlreadyActiveError("Esa persona ya tiene una invitación vigente.")
            if access_expires_at is None:
                days = access_days or (await uow.settings.load()).default_guest_access_days
                access_expires_at = now + timedelta(days=days)
            invitation = await uow.invitations.add(
                Invitation.create(
                    email=email,
                    invited_by=invited_by,
                    access_expires_at=access_expires_at,
                    now=now,
                    invitee_name=invitee_name,
                )
            )
            if invitation.id is None:
                raise ValueError("la invitación no se guardó")
            await record_audit(
                uow,
                AuditAction.INVITATION_CREATED,
                target=AuditTarget.INVITATION,
                target_id=invitation.id,
                actor_id=invited_by,
                details={"access_expires_at": access_expires_at.isoformat()},
                now=now,
            )
            uow.record(InvitationCreated(invitation_id=invitation.id, occurred_at=now))
            await uow.commit()
        return invitation
