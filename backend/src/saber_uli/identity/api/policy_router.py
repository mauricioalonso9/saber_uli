"""Política de tratamiento de datos (contrato: `getCurrentPolicy` y `getPolicyVersion`, públicas;
`publishPolicyVersion`, con `policy:publish` y sesión privilegiada)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from saber_uli.identity.application.consent import PrivacyPolicyService
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.permissions import Permission
from saber_uli.identity.domain.policy import (
    BODY_MAX_LENGTH,
    BODY_MIN_LENGTH,
    TITLE_MAX_LENGTH,
    PolicyVersion,
)
from saber_uli.shared.api.auth import require_permission, require_privileged

router = APIRouter(prefix="/api/v1", tags=["policy"])


class PolicyVersionOut(BaseModel):
    id: UUID
    version: str
    title: str
    body_markdown: str
    effective_from: datetime

    @classmethod
    def of(cls, version: PolicyVersion) -> "PolicyVersionOut":
        if version.id is None:
            raise ValueError("La versión de la política no está guardada.")
        return cls(
            id=version.id,
            version=version.version,
            title=version.title,
            body_markdown=version.body_markdown,
            effective_from=version.effective_from,
        )


class PolicyVersionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+$")]
    title: Annotated[str, Field(max_length=TITLE_MAX_LENGTH)]
    body_markdown: Annotated[str, Field(min_length=BODY_MIN_LENGTH, max_length=BODY_MAX_LENGTH)]
    effective_from: AwareDatetime


def _service(request: Request) -> PrivacyPolicyService:
    service: PrivacyPolicyService = request.app.state.privacy_policy_service
    return service


Service = Annotated[PrivacyPolicyService, Depends(_service)]


@router.get("/privacy-policy/current", operation_id="getCurrentPolicy")
async def get_current_policy(service: Service) -> PolicyVersionOut:
    return PolicyVersionOut.of(await service.current())


@router.get("/privacy-policy/versions/{policy_version_id}", operation_id="getPolicyVersion")
async def get_policy_version(policy_version_id: UUID, service: Service) -> PolicyVersionOut:
    return PolicyVersionOut.of(await service.get(policy_version_id))


@router.post(
    "/admin/privacy-policy/versions",
    operation_id="publishPolicyVersion",
    status_code=201,
    tags=["admin"],
)
async def publish_policy_version(
    body: PolicyVersionIn,
    # Primero el permiso (403) y después la sesión privilegiada (401).
    admin: Annotated[
        AuthenticatedUser, Depends(require_permission(Permission.POLICY_PUBLISH.value))
    ],
    _: Annotated[AuthenticatedUser, Depends(require_privileged)],
    service: Service,
) -> PolicyVersionOut:
    published = await service.publish(
        admin.id,
        version=body.version,
        title=body.title,
        body_markdown=body.body_markdown,
        effective_from=body.effective_from,
    )
    return PolicyVersionOut.of(published)
