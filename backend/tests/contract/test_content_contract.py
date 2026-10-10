"""T005: la implementación del banco de ítems cumple su contrato (principio III; research R-15).

Schemathesis genera peticiones desde `specs/002-banco-items/contracts/openapi.yaml` y las envía a
la app ASGI completa, con PostgreSQL y Redis reales, como un administrador con sesión privilegiada
(tiene `content:author`, `content:review` y `content:taxonomy_manage`). Se prueban las operaciones
de `implemented_content_operations.py`; desde T112 deben ser todas las del contrato.

Además, ninguna ruta `/api/v1/content` de la app puede quedar fuera del contrato.
"""

import io
from typing import Any

import pytest
import schemathesis
from schemathesis.specs.openapi.checks import (
    allow_header_conformance,
    missing_required_header,
    positive_data_acceptance,
    response_schema_conformance,
    unsupported_method,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from saber_uli.main import create_app
from tests.contract.implemented_content_operations import IMPLEMENTED_CONTENT_OPERATIONS
from tests.contract.test_openapi_contract import Unlimited
from tests.integration.conftest import REPO, CommittedLogin, settings_for
from tests.routes import app_operations

CONTRACT = REPO / "specs" / "002-banco-items" / "contracts" / "openapi.yaml"
CONTENT_PREFIX = "/api/v1/content"


# Operaciones cuyas reglas no caben en el esquema: datos que lo cumplen pueden violar las reglas
# del banco (módulo, categorías, opciones por parte; FR-024) y responder 422, como documenta el
# contrato; una imagen debe además ser PNG, JPEG o WebP de verdad y responde 415 (R-11).
BEYOND_SCHEMA = frozenset(
    {
        "uploadContentMedia",
        "createItem",
        "saveItemDraft",
        "submitItem",
        "createContext",
        "updateContext",
        "createImport",
        # La categoría padre debe ser del tipo y módulo correctos (FR-001). Además, PostgreSQL no
        # guarda texto con el carácter NUL ni sustitutos UTF-16 sueltos, que el esquema admite.
        "createTaxonomyNode",
        "updateTaxonomyNode",
        "createRubric",
        "updateRubric",
    }
)


# Descargas cuyo cuerpo es un archivo: el contrato lo declara binario (`format: binary`) aun en
# `application/json`, y Schemathesis validaría el JSON del archivo contra `type: string`.
FILE_DOWNLOADS = frozenset({"exportItems"})


def _contract_operations() -> dict[str, str]:
    """`"MÉTODO /ruta"` → `operationId` de cada operación del contrato."""
    raw = schemathesis.openapi.from_path(CONTRACT).raw_schema
    return {
        f"{method.upper()} {path}": op["operationId"]
        for path, item in raw["paths"].items()
        for method, op in item.items()
        if isinstance(op, dict) and "operationId" in op
    }


def test_las_operaciones_implementadas_existen_en_el_contrato() -> None:
    known = set(_contract_operations().values())

    assert sorted(IMPLEMENTED_CONTENT_OPERATIONS - known) == [], "operaciones fuera del contrato"


def test_ninguna_ruta_de_content_queda_fuera_del_contrato(
    migrated_database: dict[str, str], redis_url: str
) -> None:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    routes = {
        f"{method} {path}"
        for method, path in app_operations(app)
        if path.startswith(CONTENT_PREFIX)
    }

    assert routes, "la app no expone rutas de content"
    assert sorted(routes - set(_contract_operations())) == []


class BearerToken:
    """La autenticación la pone el arnés (no es un dato que Schemathesis deba mutar)."""

    token = ""

    def get(self, case: Any, context: Any) -> str:
        return self.token

    def set(self, case: Any, data: str, context: Any) -> None:
        case.headers = {**(case.headers or {}), "Authorization": f"Bearer {data}"}


@pytest.fixture
def content_contract_schema(
    migrated_database: dict[str, str], redis_url: str, redis_client: Any
) -> Any:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    app.state.rate_limiter = Unlimited()
    schema = schemathesis.openapi.from_path(CONTRACT)
    schema.app = app
    schema.auth()(BearerToken)
    return schema


@pytest.fixture
async def content_contract_headers(
    committed_login: CommittedLogin, app_engine: AsyncEngine
) -> dict[str, str]:
    admin, token = await committed_login(Role.ADMIN, priv=True)
    async with app_engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
                   SELECT :u, id, 'accepted', 'web_pwa' FROM identity.policy_versions
                   WHERE effective_from <= now() ORDER BY effective_from DESC LIMIT 1"""
            ),
            {"u": admin.id},
        )
    BearerToken.token = token
    return {"Authorization": f"Bearer {token}"}


def _partially_implemented_paths() -> set[str]:
    """Rutas del contrato con métodos que aún no existen: su cabecera Allow no coincide todavía."""
    raw = schemathesis.openapi.from_path(CONTRACT).raw_schema
    return {
        path
        for path, item in raw["paths"].items()
        if any(
            isinstance(op, dict) and op.get("operationId") not in IMPLEMENTED_CONTENT_OPERATIONS
            for op in item.values()
        )
    }


PARTIAL_PATHS = _partially_implemented_paths()


if IMPLEMENTED_CONTENT_OPERATIONS:
    content_schema = schemathesis.pytest.from_fixture("content_contract_schema").include(
        operation_id=sorted(IMPLEMENTED_CONTENT_OPERATIONS)
    )

    @content_schema.parametrize()
    def test_contrato_content(case: Any, content_contract_headers: dict[str, str]) -> None:
        excluded: list[Any] = []
        if case.operation.path in PARTIAL_PATHS:
            excluded += [unsupported_method, allow_header_conformance]
        if any(p.name == "If-Match" for p in case.operation.headers):
            # Sin If-Match la API responde 428 (RFC 6585, documentado en el contrato); la
            # comprobación genérica espera 400, 406 o 422.
            excluded.append(missing_required_header)
        operation_id = case.operation.definition.raw.get("operationId")
        if operation_id in BEYOND_SCHEMA:
            excluded.append(positive_data_acceptance)
        if operation_id in FILE_DOWNLOADS:
            excluded.append(response_schema_conformance)
        case.call_and_validate(
            headers=content_contract_headers, allow_redirects=False, excluded_checks=excluded
        )
