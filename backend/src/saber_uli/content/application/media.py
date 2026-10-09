"""Imágenes de los contextos (US3; FR-009, FR-046; research R-11).

Subir exige `content:author` (lo verifica la API). La misma imagen se guarda una vez: la huella
SHA-256 es la de la imagen ya re-codificada. Quien no es autor solo descarga las imágenes de
contenido que ya llegó a los estudiantes (versiones Publicadas o Retiradas); las demás no existen
para él (404), para no adelantar preguntas que aún no se publican.
"""

import hashlib
from collections.abc import Callable
from uuid import UUID

from saber_uli.content.application.ports import ImageProcessor
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.errors import ItemNotFoundError
from saber_uli.content.domain.media import Media
from saber_uli.shared.domain.clock import Clock

AUTHOR = "content:author"


class MediaLibrary:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], ContentUnitOfWork],
        processor: ImageProcessor,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._processor = processor
        self._clock = clock

    async def upload(self, data: bytes, actor: UUID) -> Media:
        image = self._processor.process(data)
        sha256 = hashlib.sha256(image.data).digest()
        async with self._uow_factory() as uow:
            media = await uow.media.add_or_get(
                Media(
                    id=None,
                    sha256=sha256,
                    content_type=image.content_type,
                    width=image.width,
                    height=image.height,
                    size_bytes=len(image.data),
                    data=image.data,
                    created_by=actor,
                    created_at=self._clock.now(),
                )
            )
            await uow.commit()
        return media

    async def get(self, media_id: UUID, permissions: frozenset[str]) -> Media:
        async with self._uow_factory() as uow:
            media = await uow.media.get(media_id)
            if media is not None and (AUTHOR in permissions or await uow.media.is_public(media_id)):
                return media
        raise ItemNotFoundError("La imagen no existe.")
