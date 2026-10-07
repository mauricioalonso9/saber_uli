"""`GET /api/v1/me` (contrato: `getMe`, `x-consent-exempt`)."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.application.queries.get_me import GetMe
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
