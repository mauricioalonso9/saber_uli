"""Revisión (contrato: `approveItem`, `returnItem`, `rejectItem`, `retireItem`; FR-010 a FR-015).

Permiso `content:review` (solo administradores, FR-013) con sesión privilegiada. Toda acción exige
`If-Match`; si otra persona cambió el ítem, 412 `edit-conflict` con el ítem actual (R-09).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.content.api.dependencies import Reviewer, reject_unknown_query
from saber_uli.content.api.etag import if_match_revision
from saber_uli.content.api.items_router import Code, change_item
from saber_uli.content.application.review import Review

router = APIRouter(
    prefix="/api/v1/content/items",
    tags=["items"],
    dependencies=[Depends(reject_unknown_query)],
)

Revision = Annotated[int, Depends(if_match_revision)]
ItemCode = Annotated[Code, Path(alias="itemCode")]


class ApprovalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirms_alignment: Literal[True]
    confirms_originality: Literal[True]


class CommentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str = Field(min_length=1, max_length=2000)


class ReasonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


def _review(request: Request) -> Review:
    service: Review = request.app.state.content_review
    return service


@router.post("/{itemCode}/approval", operation_id="approveItem")
async def approve_item(
    request: Request, user: Reviewer, item_code: ItemCode, revision: Revision, body: ApprovalIn
) -> JSONResponse:
    return await change_item(
        request,
        item_code,
        user,
        lambda: _review(request).approve(
            item_code,
            user.id,
            expected_revision=revision,
            confirms_alignment=body.confirms_alignment,
            confirms_originality=body.confirms_originality,
        ),
    )


@router.post("/{itemCode}/return", operation_id="returnItem")
async def return_item(
    request: Request, user: Reviewer, item_code: ItemCode, revision: Revision, body: CommentIn
) -> JSONResponse:
    return await change_item(
        request,
        item_code,
        user,
        lambda: _review(request).return_to_draft(
            item_code, user.id, expected_revision=revision, comment=body.comment
        ),
    )


@router.post("/{itemCode}/rejection", operation_id="rejectItem")
async def reject_item(
    request: Request, user: Reviewer, item_code: ItemCode, revision: Revision, body: ReasonIn
) -> JSONResponse:
    return await change_item(
        request,
        item_code,
        user,
        lambda: _review(request).reject(
            item_code, user.id, expected_revision=revision, reason=body.reason
        ),
    )


@router.post("/{itemCode}/retirement", operation_id="retireItem")
async def retire_item(
    request: Request, user: Reviewer, item_code: ItemCode, revision: Revision, body: ReasonIn
) -> JSONResponse:
    return await change_item(
        request,
        item_code,
        user,
        lambda: _review(request).retire(
            item_code, user.id, expected_revision=revision, reason=body.reason
        ),
    )
