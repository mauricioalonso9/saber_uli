"""Verificación y re-codificación de imágenes con Pillow (research R-11).

El formato se decide por el contenido, no por el nombre ni el `Content-Type`: solo PNG, JPEG o
WebP (SVG puede llevar scripts). Antes de decodificar se miran las dimensiones del encabezado,
así una imagen enorme no llega a ocupar memoria. Se re-codifica sin metadatos (EXIF puede llevar
la ubicación de la foto) después de aplicar la orientación que indicaba.
"""

import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from saber_uli.content.application.ports import ProcessedImage
from saber_uli.content.domain.errors import FileTooLargeError, UnsupportedMediaError
from saber_uli.content.domain.media import MAX_MEDIA_BYTES, MAX_MEDIA_SIDE

_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
_UNSUPPORTED = "La imagen debe ser PNG, JPEG o WebP."


class PillowImageProcessor:
    def process(self, data: bytes) -> ProcessedImage:
        if len(data) > MAX_MEDIA_BYTES:
            raise FileTooLargeError("La imagen pesa más de 1 MB.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                picture = Image.open(io.BytesIO(data), formats=tuple(_FORMATS))
                if max(picture.size) > MAX_MEDIA_SIDE:
                    raise UnsupportedMediaError("La imagen mide más de 4 000 px por lado.")
                fmt = picture.format or ""
                picture.load()
            except UnsupportedMediaError:
                raise
            except (
                UnidentifiedImageError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
                OSError,
                SyntaxError,
                ValueError,
            ):
                raise UnsupportedMediaError(_UNSUPPORTED) from None
        clean = _without_metadata(ImageOps.exif_transpose(picture), fmt)
        buffer = io.BytesIO()
        if fmt == "JPEG":
            clean.save(buffer, fmt, quality=90, optimize=True)
        elif fmt == "WEBP":
            clean.save(buffer, fmt, quality=90)
        else:
            clean.save(buffer, fmt, optimize=True)
        return ProcessedImage(
            data=buffer.getvalue(),
            content_type=_FORMATS[fmt],
            width=clean.width,
            height=clean.height,
        )


def _without_metadata(picture: Image.Image, fmt: str) -> Image.Image:
    """Copia solo los píxeles; `info` (EXIF, XMP, ICC, textos PNG) se queda atrás."""
    mode = picture.mode
    if fmt == "JPEG" and mode not in ("RGB", "L"):
        mode = "RGB"
    elif mode not in ("RGB", "RGBA", "L", "LA", "P"):
        mode = "RGBA" if "A" in picture.getbands() else "RGB"
    source = picture if picture.mode == mode else picture.convert(mode)
    clean = Image.new(source.mode, source.size)
    if source.mode == "P":
        palette = source.getpalette()
        if palette is not None:
            clean.putpalette(palette)
        if "transparency" in source.info:
            clean.info["transparency"] = source.info["transparency"]
    clean.paste(source)
    return clean
