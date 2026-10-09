"""Mis sesiones (contrato: `listMySessions`, `revokeMySession`, `revokeMyOtherSessions`; todas
`x-consent-exempt`; FR-037a, escenario 1.5; ASVS 4.0.3 V3.3.4)."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from saber_uli.identity.application.my_sessions import MySessions
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.shared.api.auth import current_user

router = APIRouter(prefix="/api/v1", tags=["me"])


class MySessionOut(BaseModel):
    id: UUID
    auth_method: Literal["entra_id", "guest_link"]
    started_at: datetime
    last_activity_at: datetime
    current: bool


class MySessionList(BaseModel):
    items: list[MySessionOut]


def _service(request: Request) -> MySessions:
    service: MySessions = request.app.state.my_sessions
    return service


Service = Annotated[MySessions, Depends(_service)]
User = Annotated[AuthenticatedUser, Depends(current_user)]


@router.get("/me/sessions", operation_id="listMySessions")
async def list_my_sessions(user: User, service: Service) -> MySessionList:
    sessions = await service.list(user.id, current=user.session_id)
    return MySessionList(
        items=[
            MySessionOut(
                id=session.id,
                auth_method=session.auth_method.value,
                started_at=session.started_at,
                last_activity_at=session.last_activity_at,
                current=session.current,
            )
            for session in sessions
        ]
    )


@router.post(
    "/me/sessions/{session_id}/revocation", operation_id="revokeMySession", status_code=204
)
async def revoke_my_session(session_id: UUID, user: User, service: Service) -> Response:
    await service.revoke(user.id, session_id)
    return Response(status_code=204)


@router.post("/me/sessions/revocation", operation_id="revokeMyOtherSessions", status_code=204)
async def revoke_my_other_sessions(user: User, service: Service) -> Response:
    await service.revoke_others(user.id, current=user.session_id)
    return Response(status_code=204)
