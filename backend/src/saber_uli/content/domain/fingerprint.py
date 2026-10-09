"""Huellas de contenido (research R-06; ADR 0008).

- `content_hash`: SHA-256 del JSON canónico (claves ordenadas, Unicode NFC, sin espacios
  externos). Dos contenidos con el mismo hash son el mismo contenido: reimportar o recargar el
  banco inicial no crea versiones (FR-035, SC-002).
- `fingerprint`: SHA-256 del texto normalizado del enunciado, de las opciones (ordenadas) y del
  contexto, sin mayúsculas, tildes, puntuación ni espacios repetidos. Detecta duplicados con
  otro código (FR-032); la paráfrasis queda fuera de alcance.
"""

import dataclasses
import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

_NON_WORD = re.compile(r"[^0-9a-z]+")


def _canonical(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _canonical(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return _canonical(value.value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value).strip()
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, list | tuple | frozenset | set):
        items = [_canonical(item) for item in value]
        return sorted(items, key=repr) if isinstance(value, frozenset | set) else items
    return value


def content_hash(value: Any) -> bytes:
    canonical = json.dumps(
        _canonical(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def normalize_text(text: str | None) -> str:
    """Minúsculas, sin tildes ni puntuación, con un solo espacio entre palabras."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", text).casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NON_WORD.sub(" ", without_marks).strip()


def fingerprint(stem: str, options: Iterable[str], context_text: str | None) -> bytes:
    parts = {
        "stem": normalize_text(stem),
        "options": sorted(normalize_text(option) for option in options),
        "context": normalize_text(context_text) if context_text is not None else None,
    }
    return content_hash(parts)
