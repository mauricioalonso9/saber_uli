"""`GET /api/v1/me` (contrato: `getMe`, `x-consent-exempt`) y `GET /api/v1/me/data-export`
(`exportMyData`, FR-031)."""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from saber_uli.identity.api.consent_router import Consent
from saber_uli.identity.api.profile_router import ProfileOut, ProgramOut
from saber_uli.identity.application.data_export import DataExport, PersonalData
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.queries.get_me import GetMe
from saber_uli.identity.domain.business_days import BOGOTA
from saber_uli.shared.api.auth import current_user

router = APIRouter(prefix="/api/v1", tags=["me"])

AccountStatus = Literal[
    "active", "disabled", "guest_expired", "guest_revoked", "deletion_pending", "deleted"
]


class Onboarding(BaseModel):
    consent_required: bool
    current_policy_version_id: UUID | None = None
    profile_required: bool


class Access(BaseModel):
    valid: bool
    validated_at: datetime
    offline_grace_until: datetime
    guest_access_expires_at: datetime | None = None
    privileged_session: bool


class Me(BaseModel):
    id: UUID
    kind: Literal["institutional", "guest"]
    status: AccountStatus
    display_name: str
    email: str
    roles: list[str]
    permissions: list[str]
    onboarding: Onboarding
    access: Access


def _get_me(request: Request) -> GetMe:
    query: GetMe = request.app.state.get_me
    return query


@router.get("/me", operation_id="getMe", response_model_exclude_none=True)
async def get_me(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
    query: Annotated[GetMe, Depends(_get_me)],
) -> Me:
    view = await query.execute(user)
    return Me(
        id=view.id,
        kind=view.kind,  # type: ignore[arg-type]
        status=view.status,  # type: ignore[arg-type]
        display_name=view.display_name,
        email=view.email,
        roles=view.roles,
        permissions=view.permissions,
        onboarding=Onboarding(
            consent_required=view.consent_required,
            current_policy_version_id=view.current_policy_version_id,
            profile_required=view.profile_required,
        ),
        access=Access(
            valid=True,
            validated_at=view.validated_at,
            offline_grace_until=view.offline_grace_until,
            guest_access_expires_at=view.guest_access_expires_at,
            privileged_session=view.privileged_session,
        ),
    )


# --- Mis datos (FR-031) -------------------------------------------------------------------------


class ExportIdentity(BaseModel):
    id: UUID
    kind: Literal["institutional", "guest"]
    display_name: str | None = None
    email: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None
    source_note: str


class ExportInvitation(BaseModel):
    accepted_at: datetime | None = None
    access_expires_at: datetime


class ExportSession(BaseModel):
    auth_method: Literal["entra_id", "guest_link"]
    started_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class ExportAuditEvent(BaseModel):
    occurred_at: datetime
    action: str
    actor: Literal["self", "staff", "system"]
    details: dict[str, Any]


class PersonalDataExport(BaseModel):
    generated_at: datetime
    identity: ExportIdentity
    profile: ProfileOut
    roles: list[str]
    groups: list[str]
    consents: list[Consent]
    invitation: ExportInvitation | None = None
    director_programs: list[ProgramOut]
    sessions: list[ExportSession]
    audit_events: list[ExportAuditEvent]
    sections: dict[str, Any]

    @classmethod
    def of(cls, data: PersonalData) -> "PersonalDataExport":
        user = data.user
        if user.id is None:
            raise ValueError("el usuario no está guardado")
        return cls(
            generated_at=data.generated_at,
            identity=ExportIdentity(
                id=user.id,
                kind=user.kind.value,
                display_name=user.display_name,
                email=user.email,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
                source_note=data.source_note,
            ),
            profile=ProfileOut.of(data.profile),
            roles=data.roles,
            groups=data.groups,
            consents=[Consent.of(entry) for entry in data.consents],
            invitation=(
                None
                if data.invitation is None
                else ExportInvitation(
                    accepted_at=data.invitation.accepted_at,
                    access_expires_at=data.invitation.access_expires_at,
                )
            ),
            director_programs=[ProgramOut.of(program) for program in data.director_programs],
            sessions=[
                ExportSession(
                    auth_method=session.auth_method.value,
                    started_at=session.auth_time,
                    last_seen_at=session.last_seen_at,
                    expires_at=session.absolute_expires_at,
                    revoked_at=session.revoked_at,
                )
                for session in data.sessions
            ],
            audit_events=[
                ExportAuditEvent(
                    occurred_at=event.occurred_at,
                    action=event.action,
                    actor=event.actor,  # type: ignore[arg-type]
                    details=event.details,
                )
                for event in data.audit_events
            ],
            sections=data.sections,
        )


def _data_export(request: Request) -> DataExport:
    service: DataExport = request.app.state.data_export
    return service


def export_filename(generated_at: datetime) -> str:
    day: date = generated_at.astimezone(BOGOTA).date()
    return f"saber-uli-mis-datos-{day.isoformat()}.json"


@router.get("/me/data-export", operation_id="exportMyData", response_model_exclude_none=True)
async def export_my_data(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
    service: Annotated[DataExport, Depends(_data_export)],
    response: Response,
) -> PersonalDataExport:
    data = await service.execute(user.id)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{export_filename(data.generated_at)}"'
    )
    response.headers["Cache-Control"] = "no-store"
    return PersonalDataExport.of(data)
