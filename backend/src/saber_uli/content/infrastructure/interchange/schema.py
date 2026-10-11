"""JSON Schema del formato de intercambio v1, generado desde los modelos (research R-03).

Regenerar el archivo versionado (desde `backend/`):

    uv run python -m saber_uli.content.infrastructure.interchange.schema \\
        > schemas/banco_items.schema.json

`tests/unit/content/test_interchange_schema.py` falla si el archivo no coincide.
"""

import json
import sys
from typing import Any

from saber_uli.content.infrastructure.interchange.models import BancoV1

DIALECT = "https://json-schema.org/draft/2020-12/schema"


def interchange_schema() -> dict[str, Any]:
    schema = BancoV1.model_json_schema(mode="validation")
    return {"$schema": DIALECT, **schema}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")  # type: ignore[union-attr]
    sys.stdout.write(json.dumps(interchange_schema(), ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
