"""Supresión de la cuenta (contrato: `getMyDeletionRequest`, `requestMyDeletion`,
`adminListDeletionRequests`).

Las dos rutas de `/me` están exentas de la autorización de datos (`x-consent-exempt`): quien la
rechazó o revocó también puede pedir la supresión. El listado del administrador exige
`deletions:read` y sesión privilegiada; muestra el UUID de la persona, sin nombre ni correo.
"""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from saber_uli.identity.api.dependencies import privileged_with
from saber_uli.identity.application.deletion import DeletionService
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.deletion_request import DeletionRequest, DeletionStatus
from saber_uli.identity.domain.permissions import Permission
from saber_uli.shared.api.auth import current_user
from saber_uli.shared.api.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/api/v1", tags=["me"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class DeletionRequestOut(BaseModel):
    id: UUID
    user_id: UUID | None = None
    status: Literal["received", "in_progress", "completed"]
    origin: Literal["user_request", "guest_retention", "institutional_retention"]
    requested_at: datetime
    due_date: date
    completed_at: datetime | None = None

    @classmethod
    def of(cls, request: DeletionRequest, *, for_admin: bool = False) -> "DeletionRequestOut":
        if request.id is None:
            raise ValueError("la solicitud no está guardada")
        return cls(
            id=request.id,
            user_id=request.user_id if for_admin else None,
            status=request.status.value,
            origin=request.origin.value,
            requested_at=request.requested_at,
            due_date=request.due_date,
            completed_at=request.completed_at,
        )


class DeletionConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: Literal["ELIMINAR"]


def _service(request: Request) -> DeletionService:
    service: DeletionService = request.app.state.deletion_service
    return service


Service = Annotated[DeletionService, Depends(_service)]
User = Annotated[AuthenticatedUser, Depends(current_user)]
DeletionReader = Annotated[AuthenticatedUser, Depends(privileged_with(Permission.DELETIONS_READ))]


@router.get(
    "/me/deletion-request",
    operation_id="getMyDeletionRequest",
    response_model_exclude_none=True,
)
async def get_my_deletion_request(user: User, service: Service) -> DeletionRequestOut:
    return DeletionRequestOut.of(await service.mine(user.id))


@router.post(
    "/me/deletion-request",
    operation_id="requestMyDeletion",
    status_code=202,
    response_model_exclude_none=True,
)
async def request_my_deletion(
    _: DeletionConfirmation, user: User, service: Service
) -> DeletionRequestOut:
    return DeletionRequestOut.of(await service.request(user.id))


@admin_router.get(
    "/deletion-requests",
    operation_id="adminListDeletionRequests",
    response_model_exclude_none=True,
)
async def admin_list_deletion_requests(
    _: DeletionReader,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    status: Annotated[Literal["received", "in_progress", "completed"] | None, Query()] = None,
) -> Page[DeletionRequestOut]:
    requests, total = await service.list(
        status=DeletionStatus(status) if status else None,
        offset=params.offset,
        limit=params.limit,
    )
    return Page.of([DeletionRequestOut.of(r, for_admin=True) for r in requests], params, total)
