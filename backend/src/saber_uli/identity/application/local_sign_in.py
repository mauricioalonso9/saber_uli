"""Ingreso y cambio de contraseña de la cuenta local de administración (US9; FR-040 a FR-047;
R-41; ADR 0009).

- `sign_in`: usuario y contraseña. Usuario inexistente, cuenta no activa y contraseña incorrecta
  dan el mismo error; la contraseña incorrecta cuenta un fallo y el décimo bloquea 15 minutos.
  Con el cambio pendiente, `SessionService` emite la sesión sin roles (FR-041).
- `change_password`: exige la contraseña actual, aplica la política (FR-042), cierra todas las
  sesiones de la cuenta y abre una nueva (FR-045).
- `reset`: el comando del servidor vuelve a la contraseña inicial con el cambio obligatorio.

La contraseña nunca llega a los registros ni a la auditoría: solo al `PasswordHasher`.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import PasswordHasher
from saber_uli.identity.application.sessions import IssuedSession, SessionService
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.events import UserAccessChanged
from saber_uli.identity.domain.local_credential import (
    INITIAL_PASSWORD,
    LOCAL_ADMIN_USERNAME,
    check_new_password,
)
from saber_uli.identity.domain.session import AuthMethod
from saber_uli.identity.domain.user import User, UserKind, UserStatus
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import (
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)

_INVALID = "El usuario o la contraseña no son correctos."


class InvalidCredentialsError(UnauthenticatedError):
    slug = "invalid-credentials"


class AccountLockedError(DomainError):
    """Diez fallos seguidos: la cuenta espera 15 minutos (FR-044). La API responde 429."""

    slug = "account-locked"

    def __init__(self, seconds: int) -> None:
        minutes = max(1, -(-seconds // 60))
        super().__init__(f"Demasiados intentos fallidos. Intenta de nuevo en {minutes} minutos.")
        self.seconds = seconds


class WrongCurrentPasswordError(PermissionDeniedError):
    slug = "invalid-credentials"


class LocalAccountNotFoundError(NotFoundError):
    slug = "not-found"


class LocalSignIn:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        hasher: PasswordHasher,
        sessions: SessionService,
        common_passwords: frozenset[str],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._hasher = hasher
        self._sessions = sessions
        self._common = common_passwords

    async def sign_in(self, username: str, password: str) -> IssuedSession:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_username(username.strip())
            credential = (
                await uow.local_credentials.get(user.id, for_update=True)
                if user is not None and user.id is not None and user.kind is UserKind.LOCAL
                else None
            )
            if user is None or user.id is None or credential is None:
                self._hasher.waste_time(password)
                await self._rejected(uow, None, "invalid_credentials", now)
                await uow.commit()
                raise InvalidCredentialsError(_INVALID)
            if credential.is_locked(now):
                await self._rejected(uow, user, "locked", now)
                await uow.commit()
                raise AccountLockedError(credential.seconds_locked(now))
            if not self._hasher.verify(credential.password_hash, password):
                locked = credential.record_failure(now)
                await uow.local_credentials.save(credential)
                await self._rejected(uow, user, "invalid_credentials", now)
                if locked:
                    await record_audit(
                        uow,
                        AuditAction.AUTH_LOCAL_LOCKED,
                        target=AuditTarget.USER,
                        target_id=user.id,
                        subject_user_id=user.id,
                        now=now,
                    )
                await uow.commit()
                raise InvalidCredentialsError(_INVALID)
            if user.status is not UserStatus.ACTIVE:
                await self._rejected(uow, user, "account_not_active", now)
                await uow.commit()
                raise InvalidCredentialsError(_INVALID)
            credential.record_success()
            if self._hasher.needs_rehash(credential.password_hash):
                credential.password_hash = self._hasher.hash(password)
            await uow.local_credentials.save(credential)
            user.record_login(now)
            await uow.users.save(user)
            await record_audit(
                uow,
                AuditAction.AUTH_LOCAL_LOGIN_SUCCEEDED,
                target=AuditTarget.USER,
                target_id=user.id,
                subject_user_id=user.id,
                now=now,
            )
            await uow.commit()
            user_id = user.id
        return await self._sessions.open_session(user_id, AuthMethod.LOCAL_PASSWORD)

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> IssuedSession:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            if user is None or user.id is None or user.kind is not UserKind.LOCAL:
                raise PermissionDeniedError("Esta cuenta no tiene contraseña propia.")
            credential = await uow.local_credentials.get(user.id, for_update=True)
            if credential is None:
                raise PermissionDeniedError("Esta cuenta no tiene contraseña propia.")
            if not self._hasher.verify(credential.password_hash, current_password):
                raise WrongCurrentPasswordError("La contraseña actual no es correcta.")
            check_new_password(
                new_password,
                username=user.username or LOCAL_ADMIN_USERNAME,
                same_as_current=self._hasher.verify(credential.password_hash, new_password),
                common=self._common,
            )
            credential.change_password(self._hasher.hash(new_password), now)
            await uow.local_credentials.save(credential)
            await _close_sessions(uow, user, now)
            await record_audit(
                uow,
                AuditAction.AUTH_PASSWORD_CHANGED,
                target=AuditTarget.USER,
                target_id=user.id,
                subject_user_id=user.id,
                actor_id=user.id,
                now=now,
            )
            await uow.commit()
            user_id = user.id
        return await self._sessions.open_session(user_id, AuthMethod.LOCAL_PASSWORD)

    @staticmethod
    async def _rejected(
        uow: IdentityUnitOfWork, user: User | None, cause: str, now: datetime
    ) -> None:
        await record_audit(
            uow,
            AuditAction.AUTH_LOGIN_REJECTED,
            target=AuditTarget.USER,
            target_id=None if user is None else user.id,
            subject_user_id=None if user is None else user.id,
            details={"provider": "local_password", "cause": cause},
            now=now,
        )


class LocalPasswordReset:
    """Comando del servidor (FR-046): no abre sesiones, así que no necesita `SessionService`."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        hasher: PasswordHasher,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._hasher = hasher

    async def reset(self, username: str = LOCAL_ADMIN_USERNAME) -> str:
        """Contraseña inicial y cambio obligatorio (FR-046); devuelve el usuario restablecido."""
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_username(username)
            credential = (
                await uow.local_credentials.get(user.id, for_update=True)
                if user is not None and user.id is not None
                else None
            )
            if user is None or user.id is None or credential is None:
                raise LocalAccountNotFoundError(f"No existe la cuenta local {username}.")
            credential.reset(self._hasher.hash(INITIAL_PASSWORD), now)
            await uow.local_credentials.save(credential)
            await _close_sessions(uow, user, now)
            await record_audit(
                uow,
                AuditAction.AUTH_PASSWORD_RESET,
                target=AuditTarget.USER,
                target_id=user.id,
                subject_user_id=user.id,
                now=now,
            )
            await uow.commit()
            return user.username or username


async def _close_sessions(uow: IdentityUnitOfWork, user: User, now: datetime) -> None:
    if user.id is None:
        return
    user.invalidate_sessions()
    await uow.users.save(user)
    await uow.sessions.revoke_all_for_user(user.id, now=now, reason="access_changed")
    uow.record(UserAccessChanged(user_id=user.id, occurred_at=now))
