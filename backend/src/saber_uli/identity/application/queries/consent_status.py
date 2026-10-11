"""Consulta del estado de la autorización de datos (FR-014; data-model §2.11)."""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.consent import consent_is_current
from saber_uli.identity.domain.user import UserKind
from saber_uli.shared.domain.clock import Clock


@dataclass(frozen=True)
class ConsentStatus:
    consent_required: bool
    current_policy_version_id: UUID | None


class ConsentStatusQuery:
    """Implementa `identity.application.public.ConsentChecker`; también la usa `/me` (T079)."""

    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def status(self, user_id: UUID) -> ConsentStatus:
        async with self._uow_factory() as uow:
            current = await uow.consents.current_policy_version_id(now=self._clock.now())
            latest = await uow.consents.latest_for_user(user_id)
            user = await uow.users.get(user_id)
        # La cuenta local de administración no tiene datos personales (US9, R-41).
        local = user is not None and user.kind is UserKind.LOCAL
        return ConsentStatus(
            consent_required=not local
            and not consent_is_current(latest, current_policy_version_id=current),
            current_policy_version_id=current,
        )

    async def has_current_consent(self, user_id: UUID) -> bool:
        return not (await self.status(user_id)).consent_required
