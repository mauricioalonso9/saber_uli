"""Imágenes de los contextos (FR-009; research R-11; data-model §2.4).

La imagen ya llega re-codificada y sin metadatos; su texto alternativo vive en la versión del
contexto que la usa. La huella SHA-256 evita guardar dos veces la misma imagen.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

MAX_MEDIA_BYTES = 1_048_576
MAX_MEDIA_SIDE = 4_000
ALLOWED_MEDIA_TYPES = ("image/png", "image/jpeg", "image/webp")


@dataclass(frozen=True)
class Media:
    id: UUID | None
    sha256: bytes
    content_type: str
    width: int
    height: int
    size_bytes: int
    data: bytes
    created_by: UUID
    created_at: datetime
