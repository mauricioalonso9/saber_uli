"""Autorización de datos del usuario (contrato: `listMyConsents`, `decideConsent`,
`revokeConsent`; todas `x-consent-exempt`)."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from saber_uli.identity.application.consent import ConsentService
from saber_uli.identity.application.ports import ConsentEntry
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.identity.domain.consent import ConsentDecision
from saber_uli.shared.api.auth import current_user

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class Consent(BaseModel):
    id: UUID
    policy_version_id: UUID
    policy_version: str
    decision: Literal["accepted", "rejected", "revoked"]
    channel: str
    decided_at: datetime

    @classmethod
    def of(cls, entry: ConsentEntry) -> "Consent":
        return cls(
            id=entry.id,
            policy_version_id=entry.policy_version_id,
            policy_version=entry.policy_version,
            decision=entry.decision.value,
            channel=entry.channel,
            decided_at=entry.decided_at,
        )


class ConsentList(BaseModel):
    current: Consent | None
    items: list[Consent]


class ConsentDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_version_id: UUID
    decision: Literal["accepted", "rejected"]


def _service(request: Request) -> ConsentService:
    service: ConsentService = request.app.state.consent_service
    return service


User = Annotated[AuthenticatedUser, Depends(current_user)]
Service = Annotated[ConsentService, Depends(_service)]


@router.get("/consents", operation_id="listMyConsents")
async def list_my_consents(user: User, service: Service) -> ConsentList:
    history = await service.history(user.id)
    return ConsentList(
        current=None if history.current is None else Consent.of(history.current),
        items=[Consent.of(entry) for entry in history.items],
    )


@router.post("/consents", operation_id="decideConsent", status_code=201)
async def decide_consent(body: ConsentDecisionIn, user: User, service: Service) -> Consent:
    entry = await service.decide(
        user.id,
        policy_version_id=body.policy_version_id,
        decision=ConsentDecision(body.decision),
    )
    return Consent.of(entry)


@router.post("/consents/revocation", operation_id="revokeConsent", status_code=201)
async def revoke_consent(user: User, service: Service) -> Consent:
    return Consent.of(await service.revoke(user.id))
