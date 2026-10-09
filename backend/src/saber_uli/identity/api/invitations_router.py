"""Invitaciones y lotes (contrato: `listInvitations`, `createInvitation`, `getInvitation`,
`updateInvitationExpiry`, `resendInvitation`, `revokeInvitation`, `validateInvitationBatch`,
`getInvitationBatch`, `confirmInvitationBatch`).

Todas exigen `invitations:manage_own` (docente) o `invitations:manage_all` (administrador) y
sesión privilegiada. El alcance se aplica en la consulta: un docente solo encuentra lo suyo.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from saber_uli.identity.application.invitation_batches import InvitationBatchService
from saber_uli.identity.application.invitations import (
    InvitationService,
    InvitationView,
    Inviter,
)
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.invitation import RENEWAL_WINDOW, Invitation, InvitationStatus
from saber_uli.identity.domain.invitation_batch import (
    BATCH_MAX_ROWS,
    BatchRowInput,
    BatchTooLargeError,
    InvalidBatchFileError,
    InvitationBatch,
    parse_csv,
)
from saber_uli.identity.domain.permissions import Permission
from saber_uli.shared.api.auth import require_permission, require_privileged
from saber_uli.shared.api.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/api/v1", tags=["invitations"])

Status = Literal["sent", "accepted", "expired", "revoked"]
_EMAIL_PATTERN = r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$"


# --- Esquemas -------------------------------------------------------------------------------


class InvitedBy(BaseModel):
    id: UUID
    display_name: str | None


class InvitationOut(BaseModel):
    id: UUID
    email: str | None
    invitee_name: str | None
    status: Status
    access_expires_at: datetime
    link_expires_at: datetime | None = None
    invited_by: InvitedBy | None
    guest_user_id: UUID | None = None
    delivery_status: Literal["queued", "sent", "failed"] | None = None
    retention_deletion_on: date | None = None
    created_at: datetime
    sent_at: datetime | None = None
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None

    @classmethod
    def of(cls, invitation: Invitation, inviter_name: str | None) -> "InvitationOut":
        if invitation.id is None:
            raise ValueError("la invitación no está guardada")
        ended = invitation.accepted_at is not None and invitation.status in (
            InvitationStatus.EXPIRED,
            InvitationStatus.REVOKED,
        )
        return cls(
            id=invitation.id,
            email=invitation.email,
            invitee_name=invitation.invitee_name,
            status=invitation.status.value,
            access_expires_at=invitation.access_expires_at,
            link_expires_at=invitation.link_expires_at,
            invited_by=(
                None
                if invitation.invited_by is None
                else InvitedBy(id=invitation.invited_by, display_name=inviter_name)
            ),
            guest_user_id=invitation.guest_user_id,
            delivery_status=invitation.last_delivery_status,  # type: ignore[arg-type]
            retention_deletion_on=(
                (invitation.access_ends_at + RENEWAL_WINDOW).date() if ended else None
            ),
            created_at=invitation.created_at,
            sent_at=invitation.sent_at,
            accepted_at=invitation.accepted_at,
            revoked_at=invitation.revoked_at,
        )


class InvitationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Annotated[str, Field(max_length=254, pattern=_EMAIL_PATTERN)]
    invitee_name: Annotated[str, Field(max_length=120)] | None = None
    access_expires_at: AwareDatetime | None = None


class ExpiryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_expires_at: AwareDatetime


class BatchRowOut(BaseModel):
    line: int
    email: str
    name: str | None = None
    access_expires_at: datetime | None = None
    result: str
    message: str | None = None


class BatchOut(BaseModel):
    id: UUID
    status: Literal["pending_confirmation", "confirmed", "expired"]
    valid_count: int
    invalid_count: int
    expires_at: datetime
    confirmed_at: datetime | None = None
    rows: list[BatchRowOut]

    @classmethod
    def of(cls, batch: InvitationBatch) -> "BatchOut":
        if batch.id is None:
            raise ValueError("el lote no está guardado")
        return cls(
            id=batch.id,
            status=batch.status.value,
            valid_count=batch.valid_count,
            invalid_count=batch.invalid_count,
            expires_at=batch.expires_at,
            confirmed_at=batch.confirmed_at,
            rows=[
                BatchRowOut(
                    line=row.line,
                    email=row.email,
                    name=row.name,
                    access_expires_at=row.access_expires_at,
                    result=row.result.value,
                    message=row.message,
                )
                for row in batch.rows
            ],
        )


class BatchJsonRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Annotated[str, Field(max_length=254)]
    name: Annotated[str, Field(max_length=120)] | None = None
    access_expires_at: AwareDatetime | None = None


class BatchJsonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_access_expires_at: AwareDatetime | None = None
    rows: Annotated[list[BatchJsonRow], Field(min_length=1)]


# --- Dependencias ---------------------------------------------------------------------------


async def _inviter(
    user: Annotated[
        AuthenticatedUser,
        Depends(
            require_permission(
                Permission.INVITATIONS_MANAGE_OWN.value, Permission.INVITATIONS_MANAGE_ALL.value
            )
        ),
    ],
    _: Annotated[AuthenticatedUser, Depends(require_privileged)],
) -> Inviter:
    return Inviter(
        user_id=user.id, is_admin=Permission.INVITATIONS_MANAGE_ALL.value in user.permissions
    )


def _invitations(request: Request) -> InvitationService:
    service: InvitationService = request.app.state.invitation_service
    return service


def _batches(request: Request) -> InvitationBatchService:
    service: InvitationBatchService = request.app.state.invitation_batch_service
    return service


Who = Annotated[Inviter, Depends(_inviter)]
Invitations = Annotated[InvitationService, Depends(_invitations)]
Batches = Annotated[InvitationBatchService, Depends(_batches)]


def _out(view: InvitationView) -> InvitationOut:
    return InvitationOut.of(view.invitation, view.inviter_name)


async def _view(service: InvitationService, who: Inviter, invitation: Invitation) -> InvitationOut:
    if invitation.id is None:  # pragma: no cover - las invitaciones del servicio están guardadas
        raise ValueError("la invitación no está guardada")
    return _out(await service.view(who, invitation.id))


# --- Invitaciones ---------------------------------------------------------------------------


@router.get("/invitations", operation_id="listInvitations")
async def list_invitations(
    who: Who,
    service: Invitations,
    params: Annotated[PageParams, Depends(page_params)],
    status: Annotated[Status | None, Query()] = None,
    invited_by: Annotated[UUID | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=254)] = None,
) -> Page[InvitationOut]:
    items, total = await service.list(
        who,
        status=InvitationStatus(status) if status else None,
        q=q,
        invited_by=invited_by,
        offset=params.offset,
        limit=params.limit,
    )
    return Page.of([_out(item) for item in items], params, total)


@router.post("/invitations", operation_id="createInvitation", status_code=201)
async def create_invitation(body: InvitationIn, who: Who, service: Invitations) -> InvitationOut:
    created = await service.create(
        who,
        email=body.email,
        invitee_name=body.invitee_name,
        access_expires_at=body.access_expires_at,
    )
    return await _view(service, who, created)


@router.get("/invitations/{invitation_id}", operation_id="getInvitation")
async def get_invitation(invitation_id: UUID, who: Who, service: Invitations) -> InvitationOut:
    return _out(await service.view(who, invitation_id))


@router.patch("/invitations/{invitation_id}", operation_id="updateInvitationExpiry")
async def update_invitation_expiry(
    invitation_id: UUID, body: ExpiryIn, who: Who, service: Invitations
) -> InvitationOut:
    changed = await service.change_expiry(who, invitation_id, body.access_expires_at)
    return await _view(service, who, changed)


@router.post(
    "/invitations/{invitation_id}/resend", operation_id="resendInvitation", status_code=202
)
async def resend_invitation(invitation_id: UUID, who: Who, service: Invitations) -> InvitationOut:
    return await _view(service, who, await service.resend(who, invitation_id))


@router.post("/invitations/{invitation_id}/revocation", operation_id="revokeInvitation")
async def revoke_invitation(invitation_id: UUID, who: Who, service: Invitations) -> InvitationOut:
    return await _view(service, who, await service.revoke(who, invitation_id))


# --- Lotes ----------------------------------------------------------------------------------


async def _batch_rows(request: Request) -> tuple[list[BatchRowInput], datetime | None]:
    """CSV (`text/csv`) o JSON equivalente; otra cosa es un dato inválido."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    raw = await request.body()
    if content_type == "text/csv":
        try:
            return parse_csv(raw.decode("utf-8")), None
        except UnicodeDecodeError as error:
            raise InvalidBatchFileError("El archivo debe estar en UTF-8.") from error
    if content_type != "application/json":
        raise InvalidBatchFileError("Envía un CSV (text/csv) o JSON.")
    try:
        payload: Any = BatchJsonIn.model_validate_json(raw)
    except ValidationError as error:
        if any(e.get("type") == "too_long" and e.get("loc") == ("rows",) for e in error.errors()):
            raise BatchTooLargeError(f"El lote admite hasta {BATCH_MAX_ROWS} filas.") from error
        raise InvalidBatchFileError("Revisa las filas del lote.") from error
    if len(payload.rows) > BATCH_MAX_ROWS:
        raise BatchTooLargeError(f"El lote admite hasta {BATCH_MAX_ROWS} filas.")
    rows = [
        BatchRowInput(
            line=index, email=row.email, name=row.name, access_expires_at=row.access_expires_at
        )
        for index, row in enumerate(payload.rows, start=1)
    ]
    return rows, payload.default_access_expires_at


@router.post("/invitation-batches", operation_id="validateInvitationBatch", status_code=201)
async def validate_invitation_batch(request: Request, who: Who, service: Batches) -> BatchOut:
    rows, default = await _batch_rows(request)
    return BatchOut.of(await service.validate(who, rows, default_access_expires_at=default))


@router.get("/invitation-batches/{batch_id}", operation_id="getInvitationBatch")
async def get_invitation_batch(batch_id: UUID, who: Who, service: Batches) -> BatchOut:
    return BatchOut.of(await service.get(who, batch_id))


@router.post("/invitation-batches/{batch_id}/confirmation", operation_id="confirmInvitationBatch")
async def confirm_invitation_batch(batch_id: UUID, who: Who, service: Batches) -> BatchOut:
    return BatchOut.of(await service.confirm(who, batch_id))
