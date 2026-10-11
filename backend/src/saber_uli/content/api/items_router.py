"""Ítems: listado, detalle, historia, versiones, comentarios y autoría (contrato: `listItems`,
`getItem`, `getItemHistory`, `getItemVersion`, `commentItem`, `createItem`, `saveItemDraft` y
`submitItem`). Permiso `content:author` (R-08).

Guardar y enviar exigen `If-Match`; si otra persona cambió el ítem, 412 `edit-conflict` con el ítem
actual (R-09, FR-027).
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from saber_uli.content.api import schemas
from saber_uli.content.api.dependencies import Author, reject_unknown_query
from saber_uli.content.api.etag import edit_conflict, etag, if_match_revision
from saber_uli.content.api.inputs import ItemContentIn, ItemCreateIn
from saber_uli.content.application.authoring import Authoring
from saber_uli.content.application.ports import ItemFilters
from saber_uli.content.application.queries.items import (
    GetItem,
    ItemHistoryQuery,
    ListItems,
    Viewer,
)
from saber_uli.content.application.review import Review
from saber_uli.content.domain.errors import EditConflictError
from saber_uli.content.domain.item import Item
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.shared.api.pagination import PageParams, page_params

router = APIRouter(
    prefix="/api/v1/content/items",
    tags=["items"],
    dependencies=[Depends(reject_unknown_query)],
)

Code = Annotated[str, Path(pattern=r"^[A-Z]{2,3}(-[A-Z0-9]+){1,3}$", max_length=32)]


class CommentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str = Field(min_length=1, max_length=2000)


def viewer(user: AuthenticatedUser) -> Viewer:
    return Viewer(id=user.id, permissions=frozenset(user.permissions))


def item_response(body: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(body, status_code=status_code, headers={"ETag": etag(body["revision"])})


async def current_item(request: Request, code: str, user: AuthenticatedUser) -> dict[str, Any]:
    service: GetItem = request.app.state.content_get_item
    return schemas.item(await service.execute(code, viewer(user)))


async def change_item(
    request: Request, code: str, user: AuthenticatedUser, action: Callable[[], Awaitable[Item]]
) -> JSONResponse:
    """Aplica un cambio con bloqueo optimista y responde el ítem con su `ETag`."""
    try:
        await action()
    except EditConflictError:
        current = await current_item(request, code, user)
        raise edit_conflict(current, revision=current["revision"]) from None
    return item_response(await current_item(request, code, user))


def _authoring(request: Request) -> Authoring:
    service: Authoring = request.app.state.content_authoring
    return service


ItemCode = Annotated[Code, Path(alias="itemCode")]
Revision = Annotated[int, Depends(if_match_revision)]


@router.get("", operation_id="listItems")
async def list_items(
    request: Request,
    user: Author,
    paging: Annotated[PageParams, Depends(page_params)],
    module: Annotated[Literal["LC", "RC", "CC", "ING", "CE"] | None, Query()] = None,
    state: Annotated[Literal["draft", "in_review", "published", "retired"] | None, Query()] = None,
    origin: Annotated[Literal["seed", "teacher", "ai"] | None, Query()] = None,
    difficulty: Annotated[Literal["low", "medium", "high"] | None, Query()] = None,
    taxonomy_node: Annotated[UUID | None, Query()] = None,
    signal: Annotated[
        Literal["too_easy", "too_hard", "negative_discrimination", "distractor_beats_key"] | None,
        Query(),
    ] = None,
    awaiting_my_review: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    service: ListItems = request.app.state.content_list_items
    filters = ItemFilters(
        module=module,
        state=state,
        origin=origin,
        difficulty=difficulty,
        signal=signal,
        q=_search_text(q),
        awaiting_review_of=user.id if awaiting_my_review else None,
    )
    page = await service.execute(
        filters, taxonomy_node=taxonomy_node, offset=paging.offset, limit=paging.page_size
    )
    return {
        "items": [schemas.item_summary(summary) for summary in page.items],
        "meta": {"page": paging.page, "page_size": paging.page_size, "total": page.total},
    }


@router.post("", operation_id="createItem", status_code=201)
async def create_item(request: Request, user: Author, body: ItemCreateIn) -> JSONResponse:
    await _authoring(request).create(
        code=body.code,
        module=body.module,
        kind=body.item_kind,
        content=body.content.to_domain(),
        actor=user.id,
    )
    return item_response(await current_item(request, body.code, user), status_code=201)


@router.put("/{itemCode}/draft", operation_id="saveItemDraft")
async def save_item_draft(
    request: Request,
    user: Author,
    item_code: ItemCode,
    revision: Revision,
    body: ItemContentIn,
    keep_in_review: Annotated[bool, Query()] = False,
) -> JSONResponse:
    return await change_item(
        request,
        item_code,
        user,
        lambda: _authoring(request).save_draft(
            item_code,
            body.to_domain(),
            user.id,
            expected_revision=revision,
            keep_in_review=keep_in_review,
        ),
    )


@router.post("/{itemCode}/submission", operation_id="submitItem")
async def submit_item(
    request: Request, user: Author, item_code: ItemCode, revision: Revision
) -> JSONResponse:
    return await change_item(
        request,
        item_code,
        user,
        lambda: _authoring(request).submit(item_code, user.id, expected_revision=revision),
    )


@router.get("/{itemCode}", operation_id="getItem")
async def get_item(
    request: Request, user: Author, item_code: Annotated[Code, Path(alias="itemCode")]
) -> JSONResponse:
    return item_response(await current_item(request, item_code, user))


@router.get("/{itemCode}/history", operation_id="getItemHistory")
async def get_item_history(
    request: Request, _: Author, item_code: Annotated[Code, Path(alias="itemCode")]
) -> dict[str, Any]:
    service: ItemHistoryQuery = request.app.state.content_item_history
    return schemas.history(await service.history(item_code))


@router.get("/{itemCode}/versions/{versionNumber}", operation_id="getItemVersion")
async def get_item_version(
    request: Request,
    _: Author,
    item_code: Annotated[Code, Path(alias="itemCode")],
    version_number: Annotated[int, Path(alias="versionNumber", ge=1)],
) -> dict[str, Any]:
    service: ItemHistoryQuery = request.app.state.content_item_history
    return schemas.version_details(await service.version(item_code, version_number))


@router.post("/{itemCode}/comments", operation_id="commentItem", status_code=201)
async def comment_item(
    request: Request,
    user: Author,
    item_code: Annotated[Code, Path(alias="itemCode")],
    body: CommentIn,
) -> dict[str, Any]:
    service: Review = request.app.state.content_review
    created = await service.comment(item_code, user.id, body.comment)
    names = await request.app.state.content_user_names.display_names({user.id})
    return schemas.event(created, names)


def _search_text(q: str | None) -> str | None:
    """PostgreSQL no admite el carácter NUL en un texto; se quita en vez de fallar."""
    text = (q or "").replace(chr(0), "").strip()
    return text or None
