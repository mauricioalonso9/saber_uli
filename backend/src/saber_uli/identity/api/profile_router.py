"""Perfil propio y catálogo de programas (contrato: `getMyProfile`, `updateMyProfile`,
`listActivePrograms`)."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.identity.application.profile import ProfileService, ProfileView, ProgramCatalog
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.profile import (
    GUEST_NAME_MAX,
    GUEST_NAME_MIN,
    SEMESTER_MAX,
    SEMESTER_MIN,
    DailyGoal,
    ProfileData,
)
from saber_uli.identity.domain.program import Program
from saber_uli.shared.api.auth import current_user

router = APIRouter(prefix="/api/v1")

Goal = Literal["casual", "regular", "intense"]


class ProgramOut(BaseModel):
    id: UUID
    code: str
    name: str
    campus: str
    active: bool

    @classmethod
    def of(cls, program: Program) -> "ProgramOut":
        if program.id is None:
            raise ValueError("El programa no está guardado.")
        return cls(
            id=program.id,
            code=program.code,
            name=program.name,
            campus=program.campus,
            active=program.active,
        )


class ProfileOut(BaseModel):
    program: ProgramOut | None = None
    semester: int | None = None
    expected_exam_date: date | None = None
    daily_goal: Goal
    guest_display_name: str | None = None
    complete: bool

    @classmethod
    def of(cls, view: ProfileView) -> "ProfileOut":
        profile = view.profile
        return cls(
            program=None if view.program is None else ProgramOut.of(view.program),
            semester=profile.semester,
            expected_exam_date=profile.expected_exam_date,
            # Sin perfil todavía, se propone la meta regular (el contrato la exige).
            daily_goal=(profile.daily_goal or DailyGoal.REGULAR).value,
            guest_display_name=profile.guest_display_name,
            complete=view.complete,
        )


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: UUID | None = None
    semester: Annotated[int, Field(ge=SEMESTER_MIN, le=SEMESTER_MAX)] | None = None
    expected_exam_date: date | None = None
    daily_goal: Goal
    guest_display_name: (
        Annotated[str, Field(min_length=GUEST_NAME_MIN, max_length=GUEST_NAME_MAX)] | None
    ) = None


def _profiles(request: Request) -> ProfileService:
    service: ProfileService = request.app.state.profile_service
    return service


def _catalog(request: Request) -> ProgramCatalog:
    catalog: ProgramCatalog = request.app.state.program_catalog
    return catalog


User = Annotated[AuthenticatedUser, Depends(current_user)]
Profiles = Annotated[ProfileService, Depends(_profiles)]


@router.get(
    "/me/profile", operation_id="getMyProfile", tags=["me"], response_model_exclude_none=True
)
async def get_my_profile(user: User, service: Profiles) -> ProfileOut:
    return ProfileOut.of(await service.get(user.id))


@router.put(
    "/me/profile", operation_id="updateMyProfile", tags=["me"], response_model_exclude_none=True
)
async def update_my_profile(body: ProfileIn, user: User, service: Profiles) -> ProfileOut:
    data = ProfileData(
        daily_goal=DailyGoal(body.daily_goal),
        program_id=body.program_id,
        semester=body.semester,
        expected_exam_date=body.expected_exam_date,
        guest_display_name=body.guest_display_name,
    )
    return ProfileOut.of(await service.update(user.id, data))


@router.get("/programs", operation_id="listActivePrograms", tags=["programs"])
async def list_active_programs(
    _: User, catalog: Annotated[ProgramCatalog, Depends(_catalog)]
) -> list[ProgramOut]:
    return [ProgramOut.of(program) for program in await catalog.list_active()]
