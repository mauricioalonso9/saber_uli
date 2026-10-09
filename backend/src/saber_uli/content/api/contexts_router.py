"""Contextos compartidos (contrato: `createContext`, `getContext`, `updateContext`; FR-005,
FR-020, FR-026). Permiso `content:author` con sesión privilegiada.

Editar exige `If-Match`: crea una versión nueva del contexto y responde qué ítems recibieron una
versión nueva En revisión y cuáles pasaron a la nueva versión del contexto.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse

from saber_uli.content.api import schemas
from saber_uli.content.api.dependencies import Author, reject_unknown_query
from saber_uli.content.api.etag import edit_conflict, etag, if_match_revision
from saber_uli.content.api.inputs import BusinessCode, ContextContentIn, ContextCreateIn
from saber_uli.content.application.contexts import Contexts
from saber_uli.content.domain.errors import EditConflictError

router = APIRouter(
    prefix="/api/v1/content/contexts",
    tags=["contexts"],
    dependencies=[Depends(reject_unknown_query)],
)

ContextCode = Annotated[BusinessCode, Path(alias="contextCode")]
Revision = Annotated[int, Depends(if_match_revision)]


def _contexts(request: Request) -> Contexts:
    service: Contexts = request.app.state.content_contexts
    return service


def _response(body: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(body, status_code=status_code, headers={"ETag": etag(body["revision"])})


async def _current(request: Request, code: str) -> dict[str, Any]:
    return schemas.context(await _contexts(request).get(code))


@router.post("", operation_id="createContext", status_code=201)
async def create_context(request: Request, user: Author, body: ContextCreateIn) -> JSONResponse:
    await _contexts(request).create(
        code=body.code, module=body.module, content=body.to_domain(), actor=user.id
    )
    return _response(await _current(request, body.code), status_code=201)


@router.get("/{contextCode}", operation_id="getContext")
async def get_context(request: Request, _: Author, context_code: ContextCode) -> JSONResponse:
    return _response(await _current(request, context_code))


@router.put("/{contextCode}", operation_id="updateContext")
async def update_context(
    request: Request,
    user: Author,
    context_code: ContextCode,
    revision: Revision,
    body: ContextContentIn,
) -> JSONResponse:
    try:
        _, result = await _contexts(request).update(
            context_code, body.to_domain(), user.id, expected_revision=revision
        )
    except EditConflictError:
        current = await _current(request, context_code)
        raise edit_conflict(current, revision=current["revision"]) from None
    context = await _current(request, context_code)
    return JSONResponse(
        {
            "context": context,
            "new_review_versions": result.new_review_versions,
            "rebased_open_versions": result.rebased_open_versions,
        },
        headers={"ETag": etag(context["revision"])},
    )
