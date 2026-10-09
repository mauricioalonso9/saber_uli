"""Completar y editar el perfil; catálogo de programas activos (FR-019 a FR-022).

Completar el perfil por primera vez cierra el primer ingreso (`onboarding_completed_at`); editarlo
después no cambia esa fecha. El nombre de un invitado pasa a ser su nombre visible; el de un
institucional sigue siendo el del directorio (FR-021).
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.profile import Profile, ProfileData, ProgramRef
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.user import User, UserKind
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import UnauthenticatedError


@dataclass(frozen=True)
class ProfileView:
    profile: Profile
    program: Program | None
    complete: bool


class ProfileService:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def get(self, user_id: UUID) -> ProfileView:
        async with self._uow_factory() as uow:
            user = await self._user(uow, user_id)
            profile = await uow.profiles.get(user_id) or Profile(user_id=user_id)
            return await self._view(uow, user, profile)

    async def update(self, user_id: UUID, data: ProfileData) -> ProfileView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await self._user(uow, user_id)
            profile = await uow.profiles.get(user_id) or Profile(user_id=user_id)
            program = await uow.programs.get(data.program_id) if data.program_id else None
            chosen = (
                ProgramRef(id=program.id, active=program.active)
                if program is not None and program.id is not None
                else None
            )
            profile.update(user.kind, data, program=chosen)
            await uow.profiles.save(profile)
            if user.kind is UserKind.GUEST and profile.guest_display_name:
                user.rename_guest(profile.guest_display_name)
            if profile.is_complete(user.kind):
                user.complete_onboarding(now)
            await uow.users.save(user)
            view = await self._view(uow, user, profile)
            await uow.commit()
        return view

    @staticmethod
    async def _user(uow: IdentityUnitOfWork, user_id: UUID) -> User:
        user = await uow.users.get(user_id)
        if user is None:
            raise UnauthenticatedError("La sesión no es válida.")
        return user

    @staticmethod
    async def _view(uow: IdentityUnitOfWork, user: User, profile: Profile) -> ProfileView:
        program = await uow.programs.get(profile.program_id) if profile.program_id else None
        return ProfileView(
            profile=profile, program=program, complete=profile.is_complete(user.kind)
        )


class ProgramCatalog:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def list_active(self) -> list[Program]:
        async with self._uow_factory() as uow:
            return await uow.programs.list_active()
