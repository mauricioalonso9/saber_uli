"""Ingreso de invitados con enlaces de un solo uso (FR-007, FR-011, FR-013; research R-18, R-19).

- `GuestSignIn`: consume el enlace del correo. Si la invitación está pendiente, crea la cuenta del
  invitado (solo rol Invitado) y la acepta; si ya estaba aceptada, comprueba que el acceso siga
  vigente. Luego abre la sesión como cualquier otro ingreso.
- `RequestSignInLink`: un invitado vigente pide un enlace nuevo. El resultado es el mismo exista
  o no el correo (FR-013); solo se registra `SignInLinkRequested` (sin correo ni token) para que
  el worker emita el enlace y lo envíe.
"""

from collections.abc import Callable
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import LinkTokenGenerator
from saber_uli.identity.application.sessions import IssuedSession, SessionService
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.access_link import AccessLinkInvalidError
from saber_uli.identity.domain.events import SignInLinkRequested
from saber_uli.identity.domain.invitation import Invitation, InvitationStatus
from saber_uli.identity.domain.session import AuthMethod
from saber_uli.identity.domain.user import UserKind, UserStatus
from saber_uli.shared.domain.clock import Clock

_INVALID = "El enlace no es válido, ya se usó o venció."


class GuestSignIn:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        tokens: LinkTokenGenerator,
        sessions: SessionService,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._tokens = tokens
        self._sessions = sessions

    async def execute(self, plaintext: str) -> IssuedSession:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            link = await uow.access_links.get_by_hash_for_update(self._tokens.hash(plaintext))
            if link is None:
                raise AccessLinkInvalidError(_INVALID)
            link.consume(now)
            invitation = await uow.invitations.get_for_update(link.invitation_id)
            if invitation is None:
                raise AccessLinkInvalidError(_INVALID)
            # Vencido o revocado: 403 con la causa, y el enlace queda sin usar (se revierte).
            invitation.ensure_access(now)
            if invitation.status is InvitationStatus.SENT:
                user_id = await self._accept(uow, invitation)
            else:
                user_id = await self._existing_guest(uow, invitation)
            await uow.access_links.save(link)
            await uow.commit()
        return await self._sessions.open_session(user_id, AuthMethod.GUEST_LINK)

    async def _accept(self, uow: IdentityUnitOfWork, invitation: Invitation) -> UUID:
        now = self._clock.now()
        email = invitation.email or ""
        # Si ya existe su cuenta (por ejemplo, una invitación renovada), se conserva el progreso.
        user = await uow.users.find_active_guest_by_email(email)
        created = user is None
        if user is None:
            user = await uow.users.add(invitation.new_guest_user(now))
        if user.id is None:
            raise ValueError("el usuario invitado no se guardó")
        invitation.accept(user.id, now)
        await uow.invitations.save(invitation)
        if created:
            await record_audit(
                uow,
                AuditAction.USER_CREATED,
                target=AuditTarget.USER,
                target_id=user.id,
                subject_user_id=user.id,
                details={"kind": UserKind.GUEST.value, "roles": ["guest"]},
                now=now,
            )
        await record_audit(
            uow,
            AuditAction.INVITATION_ACCEPTED,
            target=AuditTarget.INVITATION,
            target_id=invitation.id,
            subject_user_id=user.id,
            now=now,
        )
        return user.id

    @staticmethod
    async def _existing_guest(uow: IdentityUnitOfWork, invitation: Invitation) -> UUID:
        if invitation.guest_user_id is None:
            raise AccessLinkInvalidError(_INVALID)
        user = await uow.users.get(invitation.guest_user_id)
        if user is None or user.status is UserStatus.DELETED:
            raise AccessLinkInvalidError(_INVALID)
        return invitation.guest_user_id


class RequestSignInLink:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, email: str) -> None:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            invitation = await uow.invitations.find_active_by_email(email)
            if invitation is None or invitation.id is None or not invitation.has_access(now):
                return
            uow.record(SignInLinkRequested(invitation_id=invitation.id, occurred_at=now))
            await uow.commit()
