"""T059: la implementación cumple el contrato OpenAPI (principio III; research R-05).

Schemathesis genera peticiones desde `specs/001-identidad-acceso/contracts/openapi.yaml` (la app
no publica su propio esquema) y las envía a la app ASGI completa, con PostgreSQL y Redis reales.
Se prueban las operaciones de `implemented_operations.py`, que desde T177 deben ser todas las del
contrato. Las rutas con `bearerAuth` usan el token de un administrador con sesión privilegiada.
"""

import io
from typing import Any

import pytest
import schemathesis
from schemathesis.specs.openapi.checks import (
    negative_data_rejection,
    positive_data_acceptance,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

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
# Operaciones cuya aceptación no depende solo del esquema: reglas entre campos (institucional
# frente a invitado en `ProfileUpdate`) o datos que deben existir (el token de un enlace).
ACCEPTANCE_BEYOND_SCHEMA = {"PUT /api/v1/me/profile", "POST /api/auth/guest/sessions"}


class Unlimited:
    """Sin límite de peticiones: Schemathesis envía cientos desde la misma IP (los límites
    tienen sus propias pruebas, T035)."""

    async def hit(self, *_: Any) -> RateLimitDecision:
        return RateLimitDecision(allowed=True)

    def email_key(self, email: str) -> str:
        return "email:prueba"

    def opaque_key(self, value: str) -> str:
        return "opaque:prueba"


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
async def contract_headers(
    committed_login: CommittedLogin, app_engine: AsyncEngine
) -> dict[str, str]:
    admin, token = await committed_login(Role.ADMIN, priv=True)
    # Con la autorización de datos vigente, para llegar más allá de la guardia de FR-014.
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


def test_todas_las_operaciones_del_contrato_estan_implementadas() -> None:
    schema = schemathesis.openapi.from_path(CONTRACT)
    known = {
        op["operationId"]
        for path in schema.raw_schema["paths"].values()
        for op in path.values()
        if isinstance(op, dict) and "operationId" in op
    }

    assert sorted(known - IMPLEMENTED_OPERATIONS) == [], "operaciones del contrato sin implementar"
    assert sorted(IMPLEMENTED_OPERATIONS - known) == [], "operaciones que el contrato no tiene"


schema = schemathesis.pytest.from_fixture("contract_schema").include(
    operation_id=sorted(IMPLEMENTED_OPERATIONS)
)


@schema.parametrize()
def test_contrato(case: Any, contract_headers: dict[str, str]) -> None:
    # Las redirecciones (ingreso con Microsoft) apuntan al frontend o al proveedor: no se siguen.
    # Esas operaciones expresan éxito y error con 302 (el contrato no documenta otra cosa), así que
    # las comprobaciones de aceptación (2xx) y rechazo (4xx) no aplican a ellas.
    excluded: list[Any] = []
    if case.operation.label in REDIRECT_ONLY:
        excluded = [positive_data_acceptance, negative_data_rejection]
    elif case.operation.label in ACCEPTANCE_BEYOND_SCHEMA:
        # Datos válidos según el esquema pueden rechazarse con razón (422 por reglas entre campos,
        # 400 por un enlace que no existe). El resto de comprobaciones sí aplica.
        excluded = [positive_data_acceptance]
    case.call_and_validate(
        headers=contract_headers, allow_redirects=False, excluded_checks=excluded
    )
