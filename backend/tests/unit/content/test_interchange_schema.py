"""T025: el JSON Schema versionado coincide con los modelos que validan (research R-03).

Si cambia el formato, se regenera con:

    uv run python -m saber_uli.content.infrastructure.interchange.schema \\
        > schemas/banco_items.schema.json
"""

import json
from pathlib import Path

from saber_uli.content.infrastructure.interchange.schema import interchange_schema

SCHEMA_FILE = Path(__file__).parents[3] / "schemas" / "banco_items.schema.json"


def test_el_esquema_versionado_coincide_con_el_generado() -> None:
    assert SCHEMA_FILE.exists(), "falta backend/schemas/banco_items.schema.json"
    assert json.loads(SCHEMA_FILE.read_text(encoding="utf-8")) == interchange_schema()


def test_el_esquema_declara_su_version_y_el_dialecto() -> None:
    schema = interchange_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["esquema_version"]["const"] == "1.0"
