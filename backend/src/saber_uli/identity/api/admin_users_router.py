"""Administración de cuentas (contrato: `adminListUsers`, `adminGetUser`,
`adminUpdateUserStatus`, `adminSetUserRoles`; FR-023 a FR-026, FR-029).

Solo administradores (`users:manage`) con sesión privilegiada.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.identity.api.dependencies import privileged_with
from saber_uli.identity.api.profile_router import ProgramOut
from saber_uli.identity.application.admin_users import AdminUsersService, AdminUserView
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.permissions import Permission
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import UserKind
from saber_uli.shared.api.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])

RoleName = Literal["student", "guest", "teacher", "program_director", "admin"]
VisibleStatus = Literal[
    "active", "disabled", "guest_expired", "guest_revoked", "deletion_pending", "deleted"
]


class AdminUserOut(BaseModel):
    id: UUID
    kind: Literal["institutional", "guest"]
    status: VisibleStatus
    display_name: str | None
    email: str | None
    roles: list[RoleName]
    director_programs: list[ProgramOut]
    last_login_at: datetime | None = None
    created_at: datetime

    @classmethod
    def of(cls, view: AdminUserView) -> "AdminUserOut":
        user = view.user
        if user.id is None:
            raise ValueError("la cuenta no está guardada")
        return cls(
            id=user.id,
            kind=user.kind.value,
            status=view.status,
            display_name=user.display_name,
            email=user.email,
            roles=sorted(role.value for role in user.roles),
            director_programs=[ProgramOut.of(program) for program in view.director_programs],
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )


class StatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "disabled"]


class RolesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: Annotated[list[RoleName], Field(min_length=1)]
    director_program_ids: list[UUID] = []


def _service(request: Request) -> AdminUsersService:
    service: AdminUsersService = request.app.state.admin_users_service
    return service


Admin = Annotated[AuthenticatedUser, Depends(privileged_with(Permission.USERS_MANAGE))]
Service = Annotated[AdminUsersService, Depends(_service)]


@router.get("", operation_id="adminListUsers", response_model_exclude_none=True)
async def list_users(
    _: Admin,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=254)] = None,
    kind: Annotated[Literal["institutional", "guest"] | None, Query()] = None,
    role: Annotated[RoleName | None, Query()] = None,
    status: Annotated[VisibleStatus | None, Query()] = None,
) -> Page[AdminUserOut]:
    views, total = await service.list(
        q=q,
        kind=UserKind(kind) if kind else None,
        role=Role(role) if role else None,
        status=status,
        offset=params.offset,
        limit=params.limit,
    )
    return Page.of([AdminUserOut.of(view) for view in views], params, total)


@router.get("/{user_id}", operation_id="adminGetUser", response_model_exclude_none=True)
async def get_user(user_id: UUID, _: Admin, service: Service) -> AdminUserOut:
    return AdminUserOut.of(await service.get(user_id))


@router.patch("/{user_id}", operation_id="adminUpdateUserStatus", response_model_exclude_none=True)
async def update_user_status(
    user_id: UUID, body: StatusIn, admin: Admin, service: Service
) -> AdminUserOut:
    return AdminUserOut.of(await service.set_status(admin.id, user_id, body.status))


@router.put("/{user_id}/roles", operation_id="adminSetUserRoles", response_model_exclude_none=True)
async def set_user_roles(
    user_id: UUID, body: RolesIn, admin: Admin, service: Service
) -> AdminUserOut:
    view = await service.set_roles(
        admin.id,
        user_id,
        {Role(role) for role in body.roles},
        director_program_ids=set(body.director_program_ids),
    )
    return AdminUserOut.of(view)
