"""Implementación de `UserDirectory` (fachada pública de `identity`, FR-012)."""

from collections.abc import Callable
from uuid import UUID

from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import UserKind


class IdentityDirectory:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def _kind(self, user_id: UUID) -> UserKind | None:
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
        return None if user is None else user.kind

    async def is_institutional(self, user_id: UUID) -> bool:
        return await self._kind(user_id) is UserKind.INSTITUTIONAL

    async def is_guest(self, user_id: UUID) -> bool:
        return await self._kind(user_id) is UserKind.GUEST

    async def director_program_ids(self, user_id: UUID) -> set[UUID]:
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
        if user is None or Role.PROGRAM_DIRECTOR not in user.roles:
            return set()
        return set(user.director_program_ids)
