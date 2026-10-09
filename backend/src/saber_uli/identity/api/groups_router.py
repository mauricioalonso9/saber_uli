"""Grupos (contrato: `adminListGroups`, `adminCreateGroup`, `adminGetGroup`, `adminUpdateGroup`,
`adminListGroupMembers`, `adminAddGroupMembers`, `adminRemoveGroupMember`, `adminAddGroupTeachers`,
`adminRemoveGroupTeacher`; FR-027). Solo `groups:manage` con sesión privilegiada.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.identity.api.dependencies import privileged_with
from saber_uli.identity.application.groups import GroupService, GroupView
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.group import COHORT_MAX, DESCRIPTION_MAX, NAME_MAX, NAME_MIN
from saber_uli.identity.domain.permissions import Permission
from saber_uli.shared.api.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/api/v1/admin/groups", tags=["admin"])

Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
Description = Annotated[str, Field(max_length=DESCRIPTION_MAX)]
Cohort = Annotated[str, Field(max_length=COHORT_MAX)]


class TeacherOut(BaseModel):
    id: UUID
    display_name: str


class GroupOut(BaseModel):
    id: UUID
    name: str
    cohort_label: str | None = None
    program_id: UUID | None = None
    member_count: int
    description: str | None = None
    teachers: list[TeacherOut]
    archived_at: datetime | None = None
    created_at: datetime

    @classmethod
    def of(cls, view: GroupView) -> "GroupOut":
        group = view.group
        if group.id is None:
            raise ValueError("el grupo no está guardado")
        return cls(
            id=group.id,
            name=group.name,
            cohort_label=group.cohort_label,
            program_id=group.program_id,
            member_count=view.member_count,
            description=group.description,
            teachers=[
                TeacherOut(id=t.user_id, display_name=t.display_name or "") for t in view.teachers
            ],
            archived_at=group.archived_at,
            created_at=group.created_at,
        )


class GroupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    description: Description | None = None
    cohort_label: Cohort | None = None
    program_id: UUID | None = None


class GroupPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    description: Description | None = None
    cohort_label: Cohort | None = None
    archived: bool | None = None


class GroupMemberOut(BaseModel):
    user_id: UUID
    display_name: str | None
    email: str | None


class UserIdList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_ids: Annotated[list[UUID], Field(min_length=1, max_length=500)]


def _service(request: Request) -> GroupService:
    service: GroupService = request.app.state.group_service
    return service


Admin = Annotated[AuthenticatedUser, Depends(privileged_with(Permission.GROUPS_MANAGE))]
Service = Annotated[GroupService, Depends(_service)]


@router.get("", operation_id="adminListGroups", response_model_exclude_none=True)
async def list_groups(
    _: Admin,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[GroupOut]:
    views, total = await service.list(q=q, offset=params.offset, limit=params.limit)
    return Page.of([GroupOut.of(view) for view in views], params, total)


@router.post("", operation_id="adminCreateGroup", status_code=201, response_model_exclude_none=True)
async def create_group(body: GroupIn, admin: Admin, service: Service) -> GroupOut:
    view = await service.create(
        admin.id,
        name=body.name,
        description=body.description,
        cohort_label=body.cohort_label,
        program_id=body.program_id,
    )
    return GroupOut.of(view)


@router.get("/{group_id}", operation_id="adminGetGroup", response_model_exclude_none=True)
async def get_group(group_id: UUID, _: Admin, service: Service) -> GroupOut:
    return GroupOut.of(await service.get(group_id))


@router.patch("/{group_id}", operation_id="adminUpdateGroup", response_model_exclude_none=True)
async def update_group(
    group_id: UUID, body: GroupPatch, admin: Admin, service: Service
) -> GroupOut:
    changes = body.model_dump(exclude_unset=True)
    return GroupOut.of(await service.update(admin.id, group_id, **changes))


@router.get("/{group_id}/members", operation_id="adminListGroupMembers")
async def list_members(
    group_id: UUID,
    _: Admin,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
) -> Page[GroupMemberOut]:
    people, total = await service.members(group_id, offset=params.offset, limit=params.limit)
    items = [
        GroupMemberOut(user_id=p.user_id, display_name=p.display_name, email=p.email)
        for p in people
    ]
    return Page.of(items, params, total)


@router.post(
    "/{group_id}/members", operation_id="adminAddGroupMembers", response_model_exclude_none=True
)
async def add_members(group_id: UUID, body: UserIdList, admin: Admin, service: Service) -> GroupOut:
    return GroupOut.of(await service.add_members(admin.id, group_id, body.user_ids))


@router.delete(
    "/{group_id}/members/{user_id}", operation_id="adminRemoveGroupMember", status_code=204
)
async def remove_member(group_id: UUID, user_id: UUID, admin: Admin, service: Service) -> Response:
    await service.remove_member(admin.id, group_id, user_id)
    return Response(status_code=204)


@router.post(
    "/{group_id}/teachers", operation_id="adminAddGroupTeachers", response_model_exclude_none=True
)
async def add_teachers(
    group_id: UUID, body: UserIdList, admin: Admin, service: Service
) -> GroupOut:
    return GroupOut.of(await service.add_teachers(admin.id, group_id, body.user_ids))


@router.delete(
    "/{group_id}/teachers/{user_id}", operation_id="adminRemoveGroupTeacher", status_code=204
)
async def remove_teacher(group_id: UUID, user_id: UUID, admin: Admin, service: Service) -> Response:
    await service.remove_teacher(admin.id, group_id, user_id)
    return Response(status_code=204)
