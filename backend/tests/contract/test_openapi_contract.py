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
from schemathesis.specs.openapi.checks import (
    negative_data_rejection,
    positive_data_acceptance,
)

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.entra_id import (
    AuthorizationRequest,
    LoginFailedError,
)
from saber_uli.main import create_app
from saber_uli.shared.infrastructure.rate_limit import RateLimitDecision
from tests.contract.implemented_operations import IMPLEMENTED_OPERATIONS
from tests.integration.conftest import REPO, CommittedLogin, settings_for

CONTRACT = REPO / "specs" / "001-identidad-acceso" / "contracts" / "openapi.yaml"
REDIRECT_ONLY = {"GET /api/auth/microsoft/login", "GET /api/auth/microsoft/callback"}


class Unlimited:
    """Sin límite de peticiones: Schemathesis envía cientos desde la misma IP (los límites
    tienen sus propias pruebas, T035)."""

    async def hit(self, *_: Any) -> RateLimitDecision:
        return RateLimitDecision(allowed=True)

    def email_key(self, email: str) -> str:
        return "email:prueba"


class OfflineEntra:
    """Sustituye a Entra ID: ninguna prueba llama a Microsoft."""

    async def begin(self) -> AuthorizationRequest:
        return AuthorizationRequest(
            url="https://login.example.test/authorize?state=s",
            state="s" * 43,
            nonce="n" * 43,
            code_verifier="v" * 64,
        )

    async def complete(self, **_: Any) -> Any:
        raise LoginFailedError("código de prueba")


@pytest.fixture
def contract_schema(migrated_database: dict[str, str], redis_url: str, redis_client: Any) -> Any:
    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    app.state.entra_client = OfflineEntra()
    app.state.rate_limiter = Unlimited()
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
    # Las redirecciones (ingreso con Microsoft) apuntan al frontend o al proveedor: no se siguen.
    # Esas operaciones expresan éxito y error con 302 (el contrato no documenta otra cosa), así que
    # las comprobaciones de aceptación (2xx) y rechazo (4xx) no aplican a ellas.
    excluded = (
        [positive_data_acceptance, negative_data_rejection]
        if case.operation.label in REDIRECT_ONLY
        else []
    )
    case.call_and_validate(
        headers=contract_headers, allow_redirects=False, excluded_checks=excluded
    )
