"""Apoyo de las pruebas de importación (US4 y US5): archivos v1 y el servicio armado."""

import json
from datetime import datetime
from typing import Any

from saber_uli.content.application.bank_import import BankImport
from saber_uli.content.infrastructure.interchange.codec import READERS, JsonBundleCodec
from saber_uli.shared.domain.clock import Clock, FixedClock
from tests.integration.content.conftest import UowFactory

CONTEXT = "LC-CTX-701"


def lc_item(number: int, **overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": f"LC-{number:04d}",
        "modulo": "LC",
        "contexto_id": CONTEXT,
        "competencia": "LC-C1",
        "afirmacion": "LC-A1",
        "evidencia": "LC-E1.1",
        "dificultad": "media",
        "enunciado": f"¿Qué sostiene el autor en el párrafo {number}?",
        "opciones": [
            {
                "clave": key,
                "texto": f"Opción {key} del ítem {number}",
                "correcta": key == "A",
                "retroalimentacion": f"Porque {key}.",
            }
            for key in "ABCD"
        ],
        "explicacion": "Se apoya en el texto.",
        "origen": "docente",
    }
    item.update(overrides)
    return item


def lc_context(code: str = CONTEXT, body: str = "Un texto breve de opinión.") -> dict[str, Any]:
    return {
        "id": code,
        "modulo": "LC",
        "titulo": "Desconectar para aprender",
        "contenido_md": body,
        "tipo_texto": "continuo_informativo",
        "origen": "docente",
    }


def bank_file(items: list[dict[str, Any]], contexts: list[dict[str, Any]] | None = None) -> bytes:
    data = {
        "esquema_version": "1.0",
        "contextos": [lc_context()] if contexts is None else contexts,
        "items": items,
    }
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def importer(uow: UowFactory, clock: Clock | datetime) -> BankImport:
    return BankImport(
        uow_factory=uow,
        clock=clock if not isinstance(clock, datetime) else FixedClock(clock),
        readers=READERS,
        codec=JsonBundleCodec(),
    )
