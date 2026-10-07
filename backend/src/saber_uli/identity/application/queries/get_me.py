"""Consulta `getMe`: estado de la cuenta, roles, permisos y pasos pendientes (contrato: `Me`).

- `status` combina el estado de la cuenta con el acceso de invitado (`guest_expired`,
  `guest_revoked`), como `AccountStatus` del contrato.
- `onboarding`: autorización de datos vigente (FR-014) y perfil completo (FR-019 a FR-022).
- `access`: validado ahora; el plazo sin conexión es `validated_at + 7 días` (FR-038).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from saber_uli.identity.application.access_guard import AccountDeletedError
from saber_uli.identity.application.ports import GuestAccessStatus
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.consent import consent_is_current
from saber_uli.identity.domain.permissions import permissions_for
from saber_uli.identity.domain.user import UserKind
from saber_uli.shared.domain.clock import Clock

OFFLINE_GRACE = timedelta(days=7)


@dataclass(frozen=True)
class MeView:
    id: UUID
    kind: str
    status: str
    display_name: str
    email: str
    roles: list[str]
    permissions: list[str]
    consent_required: bool
    current_policy_version_id: UUID | None
    profile_required: bool
    validated_at: datetime
    offline_grace_until: datetime
    guest_access_expires_at: datetime | None
    privileged_session: bool


class GetMe:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, current: AuthenticatedUser) -> MeView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(current.id)
            if user is None or user.id is None:
                raise AccountDeletedError("Esta cuenta fue eliminada.")
            policy = await uow.consents.current_policy_version_id(now=now)
            latest = await uow.consents.latest_for_user(user.id)
            guest_status: GuestAccessStatus | None = None
            guest_expires: datetime | None = None
            if user.kind is UserKind.GUEST:
                guest_status = await uow.guest_access.status_for(user.id, now=now)
                guest_expires = await uow.guest_access.expires_at_for(user.id)

        status = user.status.value
        if guest_status is GuestAccessStatus.EXPIRED:
            status = "guest_expired"
        elif guest_status is GuestAccessStatus.REVOKED:
            status = "guest_revoked"
        roles = sorted(role.value for role in user.roles)
        return MeView(
            id=user.id,
            kind=user.kind.value,
            status=status,
            display_name=user.display_name or "",
            email=user.email or "",
            roles=roles,
            permissions=sorted(p.value for p in permissions_for(user.roles)),
            consent_required=not consent_is_current(latest, current_policy_version_id=policy),
            current_policy_version_id=policy,
            profile_required=user.onboarding_completed_at is None,
            validated_at=now,
            offline_grace_until=now + OFFLINE_GRACE,
            guest_access_expires_at=guest_expires,
            privileged_session=current.privileged,
        )
