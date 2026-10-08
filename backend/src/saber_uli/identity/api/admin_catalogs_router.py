"""Programas, parámetros y auditoría (contrato: `adminListPrograms`, `adminCreateProgram`,
`adminUpdateProgram`, `adminGetSettings`, `adminUpdateSettings`, `adminListAuditEvents`).

Cada grupo de rutas exige su permiso (`programs:manage`, `settings:manage`, `audit:read`) y
sesión privilegiada. La auditoría es solo lectura: no hay rutas que la modifiquen.
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from saber_uli.identity.api.dependencies import privileged_with
from saber_uli.identity.api.profile_router import ProgramOut
from saber_uli.identity.application.catalogs import (
    AuditFilters,
    AuditQuery,
    ProgramAdmin,
    SettingsAdmin,
)
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.permissions import Permission
from saber_uli.identity.domain.program import CAMPUS_MAX, CAMPUS_MIN, NAME_MAX, NAME_MIN
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.shared.api.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

ProgramName = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
Campus = Annotated[str, Field(min_length=CAMPUS_MIN, max_length=CAMPUS_MAX)]


class ProgramIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Annotated[str, Field(pattern=r"^[A-Z0-9-]{2,20}$")]
    name: ProgramName
    campus: Campus
    active: bool = True


class ProgramPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProgramName | None = None
    campus: Campus | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> "ProgramPatch":
        if not self.model_fields_set:
            raise ValueError("indica al menos un campo")
        return self


class SettingsOut(BaseModel):
    teacher_max_access_days: int
    default_guest_access_days: int
    invitation_link_ttl_days: int
    sign_in_link_ttl_minutes: int

    @classmethod
    def of(cls, settings: IdentitySettings) -> "SettingsOut":
        return cls(**settings.as_dict())


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_max_access_days: Annotated[int, Field(ge=1, le=730)] | None = None
    default_guest_access_days: Annotated[int, Field(ge=1, le=730)] | None = None
    invitation_link_ttl_days: Annotated[int, Field(ge=1, le=30)] | None = None
    sign_in_link_ttl_minutes: Annotated[int, Field(ge=5, le=10)] | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> "SettingsPatch":
        if not self.model_fields_set:
            raise ValueError("indica al menos un parámetro")
        return self


class AuditEventOut(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_id: UUID | None
    action: str
    target_type: str
    target_id: UUID | None = None
    subject_user_id: UUID | None = None
    details: dict[str, Any]


def _state(name: str) -> Any:
    def dependency(request: Request) -> Any:
        return getattr(request.app.state, name)

    return dependency


Programs = Annotated[ProgramAdmin, Depends(_state("program_admin"))]
Settings = Annotated[SettingsAdmin, Depends(_state("settings_admin"))]
Audit = Annotated[AuditQuery, Depends(_state("audit_query"))]
ProgramManager = Annotated[AuthenticatedUser, Depends(privileged_with(Permission.PROGRAMS_MANAGE))]
SettingsManager = Annotated[AuthenticatedUser, Depends(privileged_with(Permission.SETTINGS_MANAGE))]
AuditReader = Annotated[AuthenticatedUser, Depends(privileged_with(Permission.AUDIT_READ))]


# --- Programas ------------------------------------------------------------------------------


@router.get("/programs", operation_id="adminListPrograms")
async def list_programs(
    _: ProgramManager,
    service: Programs,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[ProgramOut]:
    programs, total = await service.list(q=q, offset=params.offset, limit=params.limit)
    return Page.of([ProgramOut.of(p) for p in programs], params, total)


@router.post("/programs", operation_id="adminCreateProgram", status_code=201)
async def create_program(body: ProgramIn, admin: ProgramManager, service: Programs) -> ProgramOut:
    program = await service.create(
        admin.id, code=body.code, name=body.name, campus=body.campus, active=body.active
    )
    return ProgramOut.of(program)


@router.patch("/programs/{program_id}", operation_id="adminUpdateProgram")
async def update_program(
    program_id: UUID, body: ProgramPatch, admin: ProgramManager, service: Programs
) -> ProgramOut:
    program = await service.update(
        admin.id, program_id, name=body.name, campus=body.campus, active=body.active
    )
    return ProgramOut.of(program)


# --- Parámetros -----------------------------------------------------------------------------


@router.get("/settings", operation_id="adminGetSettings")
async def get_settings(_: SettingsManager, service: Settings) -> SettingsOut:
    return SettingsOut.of(await service.get())


@router.patch("/settings", operation_id="adminUpdateSettings")
async def update_settings(
    body: SettingsPatch, admin: SettingsManager, service: Settings
) -> SettingsOut:
    changes = body.model_dump(exclude_unset=True)
    return SettingsOut.of(await service.update(admin.id, changes))


# --- Auditoría ------------------------------------------------------------------------------


@router.get("/audit-events", operation_id="adminListAuditEvents")
async def list_audit_events(
    _: AuditReader,
    service: Audit,
    params: Annotated[PageParams, Depends(page_params)],
    action: Annotated[str | None, Query(max_length=64)] = None,
    actor_id: Annotated[UUID | None, Query()] = None,
    subject_user_id: Annotated[UUID | None, Query()] = None,
    since: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    until: Annotated[AwareDatetime | None, Query(alias="to")] = None,
) -> Page[AuditEventOut]:
    records, total = await service.list(
        AuditFilters(
            action=action,
            actor_id=actor_id,
            subject_user_id=subject_user_id,
            since=since,
            until=until,
        ),
        offset=params.offset,
        limit=params.limit,
    )
    items = [
        AuditEventOut(
            id=r.id,
            occurred_at=r.occurred_at,
            actor_id=r.actor_id,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            subject_user_id=r.subject_user_id,
            details=r.details,
        )
        for r in records
    ]
    return Page.of(items, params, total)
