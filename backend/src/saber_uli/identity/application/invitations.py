"""Gestión de invitaciones (FR-006 a FR-010; escenarios 5.1 y 5.3 a 5.8; R-19, R-20).

- Alcance: un docente solo ve y gestiona las invitaciones que envió; las demás responden "no
  encontrado" (escenario 5.7). Un administrador gestiona todas. El sistema (comando
  `invite-guest`) actúa sin usuario y sin plazo máximo.
- Crear y reenviar registran un evento para el worker, que emite el enlace y envía el correo:
  aquí no se genera ningún token.
- Revocar termina el acceso y las sesiones abiertas del invitado (`auth_epoch` + 1).
- Cambiar el vencimiento amplía, reduce o renueva (dentro de 90 días) el acceso; el invitado
  conserva su progreso.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.events import (
    InvitationCreated,
    InvitationResent,
    UserAccessChanged,
)
from saber_uli.identity.domain.invitation import (
    GuestErasedError,
    InstitutionalEmailNotInvitableError,
    Invitation,
    InvitationAlreadyActiveError,
    InvitationNotFoundError,
    InvitationStatus,
    is_institutional_email,
    validate_access_expiry,
)
from saber_uli.identity.domain.user import UserStatus
from saber_uli.shared.domain.clock import Clock


@dataclass(frozen=True)
class Inviter:
    """Quien gestiona: un docente (solo lo suyo) o un administrador (todo)."""

    user_id: UUID
    is_admin: bool


@dataclass(frozen=True)
class InvitationView:
    invitation: Invitation
    inviter_name: str | None


class InvitationService:
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

    # --- Crear ----------------------------------------------------------------------------

    async def create(
        self,
        inviter: Inviter | None,
        *,
        email: str,
        invitee_name: str | None = None,
        access_expires_at: datetime | None = None,
        access_days: int | None = None,
    ) -> Invitation:
        """`inviter=None`: el sistema. Sin vencimiento, `default_guest_access_days`."""
        if is_institutional_email(email, self._domains):
            raise InstitutionalEmailNotInvitableError(
                "Las personas con correo institucional ingresan con su cuenta Unilibre."
            )
        now = self._clock.now()
        async with self._uow_factory() as uow:
            settings = await uow.settings.load()
            if access_expires_at is None:
                days = access_days or settings.default_guest_access_days
                access_expires_at = now + timedelta(days=days)
            validate_access_expiry(
                access_expires_at,
                now=now,
                is_admin=inviter is None or inviter.is_admin,
                settings=settings,
            )
            if await uow.invitations.find_active_by_email(email) is not None:
                raise InvitationAlreadyActiveError("Esa persona ya tiene una invitación vigente.")
            invitation = await uow.invitations.add(
                Invitation.create(
                    email=email,
                    invited_by=None if inviter is None else inviter.user_id,
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
                actor_id=invitation.invited_by,
                details={"access_expires_at": access_expires_at.isoformat()},
                now=now,
            )
            uow.record(InvitationCreated(invitation_id=invitation.id, occurred_at=now))
            await uow.commit()
        return invitation

    # --- Consultar ------------------------------------------------------------------------

    async def get(self, inviter: Inviter, invitation_id: UUID) -> Invitation:
        async with self._uow_factory() as uow:
            return _visible(await uow.invitations.get(invitation_id), inviter)

    async def view(self, inviter: Inviter, invitation_id: UUID) -> InvitationView:
        async with self._uow_factory() as uow:
            invitation = _visible(await uow.invitations.get(invitation_id), inviter)
            names = await _names(uow, [invitation])
        return InvitationView(invitation, _inviter_name(names, invitation))

    async def list(
        self,
        inviter: Inviter,
        *,
        status: InvitationStatus | None = None,
        q: str | None = None,
        invited_by: UUID | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[InvitationView], int]:
        # El filtro `invited_by` es solo para administradores; un docente ve siempre las suyas.
        scope = invited_by if inviter.is_admin else inviter.user_id
        async with self._uow_factory() as uow:
            items, total = await uow.invitations.search(
                invited_by=scope, status=status, q=q, offset=offset, limit=limit
            )
            names = await _names(uow, items)
        return [InvitationView(item, _inviter_name(names, item)) for item in items], total

    # --- Gestionar ------------------------------------------------------------------------

    async def change_expiry(
        self, inviter: Inviter, invitation_id: UUID, access_expires_at: datetime
    ) -> Invitation:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            invitation = _visible(await uow.invitations.get_for_update(invitation_id), inviter)
            validate_access_expiry(
                access_expires_at,
                now=now,
                is_admin=inviter.is_admin,
                settings=await uow.settings.load(),
            )
            guest = (
                await uow.users.get(invitation.guest_user_id) if invitation.guest_user_id else None
            )
            if guest is not None and guest.status in (
                UserStatus.DELETED,
                UserStatus.DELETION_PENDING,
            ):
                raise GuestErasedError("El invitado ya fue suprimido: envía una invitación nueva.")
            renewed = invitation.change_expiry(access_expires_at, now)
            await uow.invitations.save(invitation)
            if renewed and guest is not None:
                # Renovar reinicia el plazo de conservación del invitado (FR-034a).
                guest.retention_notice_sent_at = None
                await uow.users.save(guest)
            await record_audit(
                uow,
                AuditAction.INVITATION_EXPIRY_CHANGED,
                target=AuditTarget.INVITATION,
                target_id=invitation_id,
                actor_id=inviter.user_id,
                subject_user_id=invitation.guest_user_id,
                details={"access_expires_at": access_expires_at.isoformat(), "renewed": renewed},
                now=now,
            )
            await uow.commit()
        return invitation

    async def resend(self, inviter: Inviter, invitation_id: UUID) -> Invitation:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            invitation = _visible(await uow.invitations.get_for_update(invitation_id), inviter)
            invitation.resend(now)
            await uow.invitations.save(invitation)
            await record_audit(
                uow,
                AuditAction.INVITATION_RESENT,
                target=AuditTarget.INVITATION,
                target_id=invitation_id,
                actor_id=inviter.user_id,
                now=now,
            )
            uow.record(InvitationResent(invitation_id=invitation_id, occurred_at=now))
            await uow.commit()
        return invitation

    async def revoke(self, inviter: Inviter, invitation_id: UUID) -> Invitation:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            invitation = _visible(await uow.invitations.get_for_update(invitation_id), inviter)
            invitation.revoke(now)
            await uow.invitations.save(invitation)
            if invitation.guest_user_id is not None:
                guest = await uow.users.get(invitation.guest_user_id)
                if guest is not None:
                    # Las sesiones abiertas terminan en la siguiente petición (escenario 5.4).
                    guest.invalidate_sessions()
                    await uow.users.save(guest)
                    await uow.sessions.revoke_all_for_user(
                        invitation.guest_user_id, now=now, reason="access_changed"
                    )
                    uow.record(UserAccessChanged(user_id=invitation.guest_user_id, occurred_at=now))
            await record_audit(
                uow,
                AuditAction.INVITATION_REVOKED,
                target=AuditTarget.INVITATION,
                target_id=invitation_id,
                actor_id=inviter.user_id,
                subject_user_id=invitation.guest_user_id,
                now=now,
            )
            await uow.commit()
        return invitation


def _visible(invitation: Invitation | None, inviter: Inviter) -> Invitation:
    if invitation is None or (not inviter.is_admin and invitation.invited_by != inviter.user_id):
        raise InvitationNotFoundError("La invitación no existe.")
    return invitation


async def _names(
    uow: IdentityUnitOfWork, invitations: Sequence[Invitation]
) -> dict[UUID, str | None]:
    ids = {item.invited_by for item in invitations if item.invited_by is not None}
    return await uow.users.display_names(ids)


def _inviter_name(names: dict[UUID, str | None], invitation: Invitation) -> str | None:
    return None if invitation.invited_by is None else names.get(invitation.invited_by)
