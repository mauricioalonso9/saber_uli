"""T059: la implementación cumple el contrato OpenAPI (principio III; research R-05).

Schemathesis genera peticiones desde `specs/001-identidad-acceso/contracts/openapi.yaml` (la app
no publica su propio esquema) y las envía a la app ASGI completa, con PostgreSQL y Redis reales.
Solo se prueban las operaciones de `implemented_operations.py`. Las rutas con `bearerAuth` usan
el token de un administrador con sesión privilegiada.
"""

import io
from typing import Any

import pytest
import schemathesis

from saber_uli.identity.domain.roles import Role
from saber_uli.main import create_app
from tests.contract.implemented_operations import IMPLEMENTED_OPERATIONS
from tests.integration.conftest import REPO, CommittedLogin, settings_for

CONTRACT = REPO / "specs" / "001-identidad-acceso" / "contracts" / "openapi.yaml"


@pytest.fixture
def contract_schema(migrated_database: dict[str, str], redis_url: str, redis_client: Any) -> Any:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    schema = schemathesis.openapi.from_path(CONTRACT)
    schema.app = app
    return schema


@pytest.fixture
async def contract_headers(committed_login: CommittedLogin) -> dict[str, str]:
    _, token = await committed_login(Role.ADMIN, priv=True)
    return {"Authorization": f"Bearer {token}"}


def test_todas_las_operaciones_implementadas_existen_en_el_contrato() -> None:
    schema = schemathesis.openapi.from_path(CONTRACT)
    known = {
        op["operationId"]
        for path in schema.raw_schema["paths"].values()
        for op in path.values()
        if isinstance(op, dict) and "operationId" in op
    }

    assert known >= IMPLEMENTED_OPERATIONS


schema = schemathesis.pytest.from_fixture("contract_schema").include(
    operation_id=sorted(IMPLEMENTED_OPERATIONS)
)


@schema.parametrize()
def test_contrato(case: Any, contract_headers: dict[str, str]) -> None:
    case.call_and_validate(headers=contract_headers)
