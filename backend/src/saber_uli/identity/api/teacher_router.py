"""Vista del docente (contrato: `listMyTeachingGroups`, `listMyGroupStudents`; FR-027).

De sus estudiantes, el docente ve el nombre y (en specs posteriores) su progreso, nunca el
correo. Requiere `groups:read_own_students` y sesión privilegiada; un grupo ajeno es 404.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from saber_uli.identity.api.dependencies import privileged_with
from saber_uli.identity.application.groups import TeacherGroups
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.permissions import Permission
from saber_uli.shared.api.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/api/v1/teacher/groups", tags=["teacher"])


class GroupSummaryOut(BaseModel):
    id: UUID
    name: str
    cohort_label: str | None = None
    program_id: UUID | None = None
    member_count: int


class GroupStudentOut(BaseModel):
    user_id: UUID
    display_name: str
    progress: dict[str, Any] | None = None


def _query(request: Request) -> TeacherGroups:
    query: TeacherGroups = request.app.state.teacher_groups
    return query


Teacher = Annotated[
    AuthenticatedUser, Depends(privileged_with(Permission.GROUPS_READ_OWN_STUDENTS))
]
Query = Annotated[TeacherGroups, Depends(_query)]


@router.get("", operation_id="listMyTeachingGroups", response_model_exclude_none=True)
async def list_my_teaching_groups(teacher: Teacher, query: Query) -> list[GroupSummaryOut]:
    return [
        GroupSummaryOut(
            id=group.id,
            name=group.name,
            cohort_label=group.cohort_label,
            program_id=group.program_id,
            member_count=count,
        )
        for group, count in await query.groups(teacher.id)
        if group.id is not None
    ]


@router.get(
    "/{group_id}/students", operation_id="listMyGroupStudents", response_model_exclude_none=True
)
async def list_my_group_students(
    group_id: UUID,
    teacher: Teacher,
    query: Query,
    params: Annotated[PageParams, Depends(page_params)],
) -> Page[GroupStudentOut]:
    people, total = await query.students(
        teacher.id, group_id, offset=params.offset, limit=params.limit
    )
    items = [
        GroupStudentOut(user_id=person.user_id, display_name=person.display_name or "")
        for person in people
    ]
    return Page.of(items, params, total)
