"""Casos de uso de sesión: abrir, renovar y cerrar (research R-14 a R-16; FR-037, FR-038).

- `open_session`: tras un ingreso válido (Microsoft, T076; enlace de invitado, T107).
- `refresh`: valida la cuenta y el acceso de invitado, rota el token de renovación (bloqueado con
  `FOR UPDATE`), cuenta como actividad para la conservación (FR-034b/c) y emite un token de
  acceso con `priv` según R-15. Reutilizar un token rotado revoca la sesión y esa revocación se
  confirma aunque la petición falle.
- `logout`: revoca la sesión del token presentado (si existe).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saber_uli.identity.application.access_guard import (
    AccountDeletedError,
    AccountDisabledError,
)
from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import (
    ACCESS_TOKEN_TTL_SECONDS,
    AccessTokenClaims,
    AccessTokenEncoder,
    GuestAccessStatus,
    RefreshTokenGenerator,
    SessionRevocations,
)
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.invitation import GuestAccessExpiredError, GuestAccessRevokedError
from saber_uli.identity.domain.session import (
    AuthMethod,
    RefreshToken,
    Session,
    SessionExpiredError,
    SessionRevokedError,
    rotate_refresh_token,
)
from saber_uli.identity.domain.user import User, UserKind, UserStatus
from saber_uli.shared.domain.clock import Clock


@dataclass(frozen=True)
class IssuedSession:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_at: datetime


class SessionService:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        access_tokens: AccessTokenEncoder,
        refresh_tokens: RefreshTokenGenerator,
        revocations: SessionRevocations,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._access_tokens = access_tokens
        self._refresh_tokens = refresh_tokens
        self._revocations = revocations

    def seconds_until(self, moment: datetime) -> int:
        return max(0, int((moment - self._clock.now()).total_seconds()))

    async def open_session(self, user_id: UUID, method: AuthMethod) -> IssuedSession:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            if user is None or user.status is not UserStatus.ACTIVE:
                raise AccountDisabledError("La cuenta no está activa.")
            session = await uow.sessions.add(Session.start(user_id, method, now))
            plaintext, token_hash = self._refresh_tokens.new()
            token = await uow.sessions.add_refresh_token(
                RefreshToken.issue(session, token_hash=token_hash, now=now)
            )
            issued = self._issue(user, session, token, plaintext, now)
            await uow.commit()
        return issued

    async def refresh(self, plaintext: str) -> IssuedSession:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            current = await uow.sessions.get_refresh_token_for_update(
                self._refresh_tokens.hash(plaintext)
            )
            session = await uow.sessions.get(current.session_id) if current else None
            user = await uow.users.get(session.user_id) if session else None
            if current is None or session is None or user is None:
                raise SessionExpiredError("La sesión venció.")
            await self._ensure_can_continue(uow, user, now)

            new_plaintext, new_hash = self._refresh_tokens.new()
            was_revoked = session.revoked_at is not None
            try:
                new_token = rotate_refresh_token(session, current, new_hash=new_hash, now=now)
            except SessionRevokedError:
                if not was_revoked and session.revoked_reason == "token_reuse":
                    # La revocación por reutilización se confirma (y se audita) aunque la
                    # petición falle.
                    await uow.sessions.save(session)
                    await record_audit(
                        uow,
                        AuditAction.SESSION_REUSE_DETECTED,
                        target=AuditTarget.SESSION,
                        target_id=session.id,
                        subject_user_id=user.id,
                        now=now,
                    )
                    await uow.commit()
                    if session.id is not None:
                        await self._revocations.revoke(session.id)
                raise

            await uow.sessions.save_refresh_token(current)
            new_token = await uow.sessions.add_refresh_token(new_token)
            await uow.sessions.save(session)
            user.record_login(now)
            await uow.users.save(user)
            issued = self._issue(user, session, new_token, new_plaintext, now)
            await uow.commit()
        return issued

    async def logout(self, plaintext: str) -> None:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            token = await uow.sessions.get_refresh_token_for_update(
                self._refresh_tokens.hash(plaintext)
            )
            session = await uow.sessions.get(token.session_id) if token else None
            if session is None:
                return
            session.revoke(now, "logout")
            await uow.sessions.save(session)
            await uow.commit()
        if session.id is not None:
            # El token de acceso ya emitido deja de servir de inmediato (ASVS V3.3.1).
            await self._revocations.revoke(session.id)

    async def _ensure_can_continue(
        self, uow: IdentityUnitOfWork, user: User, now: datetime
    ) -> None:
        if user.status in (UserStatus.DELETED, UserStatus.DELETION_PENDING):
            raise AccountDeletedError("Esta cuenta fue eliminada.")
        if user.status is UserStatus.DISABLED:
            raise AccountDisabledError("La cuenta está desactivada.")
        if user.kind is UserKind.GUEST and user.id is not None:
            status = await uow.guest_access.status_for(user.id, now=now)
            if status is GuestAccessStatus.REVOKED:
                raise GuestAccessRevokedError("El acceso de invitado fue retirado.")
            if status is GuestAccessStatus.EXPIRED:
                raise GuestAccessExpiredError("El acceso de invitado venció.")

    def _issue(
        self,
        user: User,
        session: Session,
        token: RefreshToken,
        plaintext: str,
        now: datetime,
    ) -> IssuedSession:
        if user.id is None or session.id is None:
            raise ValueError("el usuario y la sesión deben estar guardados")
        claims = AccessTokenClaims(
            sub=user.id,
            sid=session.id,
            roles=tuple(sorted(role.value for role in user.roles)),
            epoch=user.auth_epoch,
            priv=session.is_privileged(now, roles=user.roles),
            iat=now,
        )
        return IssuedSession(
            access_token=self._access_tokens.encode(claims),
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            refresh_token=plaintext,
            refresh_expires_at=token.idle_expires_at,
        )
