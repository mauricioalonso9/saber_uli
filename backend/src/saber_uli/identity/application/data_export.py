"""Exportación de «Mis datos» (FR-031; escenarios 8.1 y 8.2; research R-26).

Reúne lo que `identity` guarda de la persona: identidad, perfil, roles, programas que dirige,
nombres de sus grupos, historial de autorizaciones, invitación de origen (invitados), sesiones y
eventos de auditoría sobre ella. No incluye datos de otras personas: ni quién la invitó, ni quién
creó sus grupos, ni quién hizo cada acción auditada (solo si fue ella, el personal o el sistema).
Los demás contextos agregan sus secciones con el `DataExportRegistry`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any
from uuid import UUID

from saber_uli.identity.application.ports import AuditRecord, ConsentEntry
from saber_uli.identity.application.profile import ProfileView
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.profile import Profile
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.session import Session
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


AUDIT_PAGE = 500


@dataclass(frozen=True)
class PersonalAuditEvent:
    occurred_at: datetime
    action: str
    actor: str  # `self`, `staff` o `system`: nunca el identificador de otra persona
    details: dict[str, Any]

    @classmethod
    def of(cls, record: AuditRecord, user_id: UUID) -> "PersonalAuditEvent":
        actor = (
            "system"
            if record.actor_id is None
            else "self"
            if record.actor_id == user_id
            else "staff"
        )
        return cls(
            occurred_at=record.occurred_at,
            action=record.action,
            actor=actor,
            details=record.details,
        )


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
    director_programs: list[Program] = field(default_factory=list)
    sessions: list[Session] = field(default_factory=list)
    audit_events: list[PersonalAuditEvent] = field(default_factory=list)
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
                director_programs=[
                    program
                    for program_id in sorted(user.director_program_ids)
                    if (program := await uow.programs.get(program_id)) is not None
                ],
                sessions=await uow.sessions.list_for_user(user_id),
                audit_events=await _audit_events(uow, user_id),
            )
        sections = await self._registry.sections(user_id)
        return replace(data, sections=sections)


async def _audit_events(uow: IdentityUnitOfWork, user_id: UUID) -> list[PersonalAuditEvent]:
    events: list[PersonalAuditEvent] = []
    offset = 0
    while True:
        records, total = await uow.audit.search(
            action=None,
            actor_id=None,
            subject_user_id=user_id,
            since=None,
            until=None,
            offset=offset,
            limit=AUDIT_PAGE,
        )
        events += [PersonalAuditEvent.of(record, user_id) for record in records]
        offset += len(records)
        if not records or offset >= total:
            return events
