"""Imágenes de los contextos (contrato: `uploadContentMedia`, `getContentMedia`; research R-11).

Subir exige `content:author` con sesión privilegiada y cuenta para el límite de 60 subidas por
hora por usuario. Descargar exige sesión; quien no es autor solo recibe imágenes de contenido
publicado o retirado (FR-046). Las imágenes no cambian nunca (su id sale de la huella), así que se
pueden guardar en caché un año.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from saber_uli.content.api.dependencies import CONTENT_AUTHOR, privileged_with, reject_unknown_query
from saber_uli.content.application.media import MediaLibrary
from saber_uli.content.domain.errors import FileTooLargeError
from saber_uli.content.domain.media import MAX_MEDIA_BYTES, Media
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.shared.api.auth import current_user
from saber_uli.shared.api.rate_limit import per_user
from saber_uli.shared.infrastructure.rate_limit import RateLimitRule

MEDIA_UPLOAD_PER_USER = RateLimitRule("content-media-user", "60/hour")
CACHE_CONTROL = "private, max-age=31536000, immutable"
PREFIX = "/api/v1/content/media"

router = APIRouter(prefix=PREFIX, tags=["contexts"], dependencies=[Depends(reject_unknown_query)])

_uploader = privileged_with(CONTENT_AUTHOR)
Uploader = Annotated[AuthenticatedUser, Depends(_uploader)]
Viewer = Annotated[AuthenticatedUser, Depends(current_user)]


def _library(request: Request) -> MediaLibrary:
    library: MediaLibrary = request.app.state.content_media
    return library


def media_body(media: Media) -> dict[str, Any]:
    return {
        "id": str(media.id),
        "content_type": media.content_type,
        "width": media.width,
        "height": media.height,
        "size_bytes": media.size_bytes,
        "url": f"{PREFIX}/{media.id}",
    }


@router.post(
    "",
    operation_id="uploadContentMedia",
    status_code=201,
    dependencies=[Depends(per_user(MEDIA_UPLOAD_PER_USER, _uploader))],
)
async def upload_content_media(request: Request, user: Uploader, file: UploadFile) -> JSONResponse:
    # Se lee un byte de más para saber si pasa del límite sin cargar archivos enormes.
    data = await file.read(MAX_MEDIA_BYTES + 1)
    if len(data) > MAX_MEDIA_BYTES:
        raise FileTooLargeError("La imagen pesa más de 1 MB.")
    media = await _library(request).upload(data, user.id)
    return JSONResponse(media_body(media), status_code=201)


@router.get("/{mediaId}", operation_id="getContentMedia")
async def get_content_media(
    request: Request, user: Viewer, media_id: Annotated[UUID, Path(alias="mediaId")]
) -> Response:
    media = await _library(request).get(media_id, frozenset(user.permissions))
    return Response(
        media.data, media_type=media.content_type, headers={"Cache-Control": CACHE_CONTROL}
    )
