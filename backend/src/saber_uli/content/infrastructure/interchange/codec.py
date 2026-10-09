"""Lectores por formato y el contenido de una importación pendiente (research R-05).

El `payload` de una importación es el formato v1 de sus entradas válidas: al confirmar se vuelve
a leer con el mismo lector, así lo que se aplica es exactamente lo que se mostró.
"""

import json
from collections.abc import Callable, Mapping
from typing import Any

from saber_uli.content.application.bundle import Bundle
from saber_uli.content.infrastructure.interchange.json_format import read_bundle, write_bundle
from saber_uli.content.infrastructure.interchange.xlsx_format import read_xlsx

READERS: Mapping[str, Callable[[bytes], Bundle]] = {"json": read_bundle, "xlsx": read_xlsx}


class JsonBundleCodec:
    def dump(self, bundle: Bundle) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(write_bundle(bundle))
        return data

    def load(self, payload: dict[str, Any]) -> Bundle:
        return read_bundle(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
