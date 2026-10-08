"""Exportación de «Mis datos» (FR-031; escenarios 8.1 y 8.2; research R-26).

Reúne lo que `identity` guarda de la persona: identidad, perfil, roles, nombres de sus grupos,
historial de autorizaciones e invitación de origen (invitados). No incluye datos de otras
personas: ni quién la invitó ni quién creó sus grupos. Los demás contextos agregan sus secciones
con el `DataExportRegistry`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any
from uuid import UUID

from saber_uli.identity.application.ports import ConsentEntry
from saber_uli.identity.application.profile import ProfileView
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.profile import Profile
from saber_uli.identity.domain.user import User, UserKind
from saber_uli.shared.application.data_export_registry import DataExportRegistry
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import UnauthenticatedError

SOURCE_NOTES = {
    UserKind.INSTITUTIONAL: (
        "Tu nombre y tu correo vienen del directorio institucional de Unilibre. Para corregirlos, "
        "escribe a la mesa de ayuda de TI de la Universidad Libre; se actualizan aquí en tu "
        "siguiente ingreso. Tu perfil lo puedes editar en Mi cuenta."
    ),
    UserKind.GUEST: (
        "Tu nombre lo indicas en tu perfil y lo puedes editar en Mi cuenta. Tu correo es el de "
        "tu invitación: si está mal, pide una invitación nueva a quien te invitó."
    ),
}


@dataclass(frozen=True)
class GuestInvitation:
    accepted_at: datetime | None
    access_expires_at: datetime


@dataclass(frozen=True)
class PersonalData:
    generated_at: datetime
    user: User
    source_note: str
    profile: ProfileView
    roles: list[str]
    groups: list[str]
    consents: list[ConsentEntry]
    invitation: GuestInvitation | None = None
    sections: dict[str, Any] = field(default_factory=dict)


class DataExport:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        registry: DataExportRegistry,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._registry = registry

    async def execute(self, user_id: UUID) -> PersonalData:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            if user is None:
                raise UnauthenticatedError("La sesión no es válida.")
            profile = await uow.profiles.get(user_id) or Profile(user_id=user_id)
            program = await uow.programs.get(profile.program_id) if profile.program_id else None
            invitation = None
            if user.kind is UserKind.GUEST:
                latest = await uow.invitations.latest_for_guest(user_id)
                if latest is not None:
                    invitation = GuestInvitation(
                        accepted_at=latest.accepted_at,
                        access_expires_at=latest.access_expires_at,
                    )
            data = PersonalData(
                generated_at=now,
                user=user,
                source_note=SOURCE_NOTES[user.kind],
                profile=ProfileView(
                    profile=profile, program=program, complete=profile.is_complete(user.kind)
                ),
                roles=sorted(role.value for role in user.roles),
                groups=await uow.groups.group_names_for(user_id),
                consents=await uow.consents.history_for_user(user_id),
                invitation=invitation,
            )
        sections = await self._registry.sections(user_id)
        return replace(data, sections=sections)
