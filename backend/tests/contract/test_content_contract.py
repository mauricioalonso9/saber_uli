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
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from saber_uli.main import create_app
from tests.contract.implemented_content_operations import IMPLEMENTED_CONTENT_OPERATIONS
from tests.contract.test_openapi_contract import Unlimited
from tests.integration.conftest import REPO, CommittedLogin, settings_for

CONTRACT = REPO / "specs" / "002-banco-items" / "contracts" / "openapi.yaml"
CONTENT_PREFIX = "/api/v1/content"


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
        f"{method} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith(CONTENT_PREFIX)
        for method in route.methods
    }

    assert sorted(routes - set(_contract_operations())) == []


@pytest.fixture
def content_contract_schema(
    migrated_database: dict[str, str], redis_url: str, redis_client: Any
) -> Any:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    app.state.rate_limiter = Unlimited()
    schema = schemathesis.openapi.from_path(CONTRACT)
    schema.app = app
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
    return {"Authorization": f"Bearer {token}"}


if IMPLEMENTED_CONTENT_OPERATIONS:
    content_schema = schemathesis.pytest.from_fixture("content_contract_schema").include(
        operation_id=sorted(IMPLEMENTED_CONTENT_OPERATIONS)
    )

    @content_schema.parametrize()
    def test_contrato_content(case: Any, content_contract_headers: dict[str, str]) -> None:
        case.call_and_validate(headers=content_contract_headers, allow_redirects=False)
