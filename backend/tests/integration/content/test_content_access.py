"""T029: acceso a las rutas del banco de ítems (research R-08; FR-013, FR-045, FR-046).

Para cada operación del contrato de 002 que la app ya implementa:

- sin token: 401;
- sin autorización de datos vigente: 403 `consent-required`;
- un estudiante: 403 `forbidden`;
- un docente: 403 en las rutas de `content:review` y `content:taxonomy_manage`;
- con el permiso pero sin sesión privilegiada: 401 `reauthentication-required`, salvo
  `GET /content/media/{mediaId}`, que cualquier usuario autenticado puede pedir.

Las operaciones que aún no existen se omiten; `listContentModules` existe desde la fase 2.
"""

import re
from typing import Any
from uuid import uuid4

import httpx
import pytest
import schemathesis
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import REPO, CommittedLogin
from tests.integration.identity.staff import StaffFactory, accept_current_policy
from tests.routes import app_operations

CONTRACT = REPO / "specs" / "002-banco-items" / "contracts" / "openapi.yaml"
PATH_VALUES = {
    "itemCode": "LC-0001",
    "contextCode": "LC-CTX-001",
    "moduleCode": "LC",
    "versionNumber": "1",
}
PUBLIC_TO_AUTHENTICATED = {"getContentMedia"}


def _operations() -> list[tuple[str, str, str, str | None, bool]]:
    raw = schemathesis.openapi.from_path(CONTRACT).raw_schema
    out = []
    for path, item in raw["paths"].items():
        for method, op in item.items():
            if isinstance(op, dict) and "operationId" in op:
                out.append(
                    (
                        op["operationId"],
                        method.upper(),
                        path,
                        op.get("x-required-permission"),
                        bool(op.get("x-requires-privileged-session")),
                    )
                )
    return out


OPERATIONS = _operations()


def concrete(path: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: PATH_VALUES.get(m.group(1), str(uuid4())), path)


def implemented(api_client: httpx.AsyncClient) -> set[tuple[str, str]]:
    app: Any = api_client._transport.app  # type: ignore[attr-defined]
    return app_operations(app)


async def call(
    client: httpx.AsyncClient, method: str, path: str, headers: dict[str, str] | None = None
) -> httpx.Response:
    return await client.request(method, concrete(path), headers=headers or {}, json={})


@pytest.fixture
async def student(committed_login: CommittedLogin, app_engine: AsyncEngine) -> dict[str, str]:
    user, token = await committed_login(Role.STUDENT, priv=False)
    assert user.id is not None
    await accept_current_policy(app_engine, user.id)
    return {"Authorization": f"Bearer {token}"}


def problem(response: httpx.Response) -> str:
    return str(response.json().get("type", "")).rsplit(":", 1)[-1]


async def test_la_lista_de_modulos_esta_conectada(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    teacher = await staff(Role.TEACHER)

    response = await api_client.get("/api/v1/content/modules", headers=teacher.headers)

    assert response.status_code == 200
    assert response.json() == {"items": []}


async def test_reglas_de_acceso_de_cada_operacion_implementada(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    student: dict[str, str],
    committed_login: CommittedLogin,
) -> None:
    teacher = await staff(Role.TEACHER)
    teacher_without_priv = await staff(Role.TEACHER, priv=False)
    admin_without_priv = await staff(Role.ADMIN, priv=False)
    _, no_consent_token = await committed_login(Role.TEACHER, priv=True)
    no_consent = {"Authorization": f"Bearer {no_consent_token}"}
    available = implemented(api_client)
    checked = 0

    for operation_id, method, path, permission, privileged in OPERATIONS:
        if (method, path) not in available:
            continue
        checked += 1
        label = f"{method} {path}"

        assert (await call(api_client, method, path)).status_code == 401, label

        if operation_id in PUBLIC_TO_AUTHENTICATED:
            continue
        refused = await call(api_client, method, path, no_consent)
        assert (refused.status_code, problem(refused)) == (403, "consent-required"), label

        denied = await call(api_client, method, path, student)
        assert (denied.status_code, problem(denied)) == (403, "forbidden"), label

        if permission in ("content:review", "content:taxonomy_manage"):
            by_teacher = await call(api_client, method, path, teacher.headers)
            assert (by_teacher.status_code, problem(by_teacher)) == (403, "forbidden"), label

        if privileged:
            holder = teacher_without_priv if permission == "content:author" else admin_without_priv
            response = await call(api_client, method, path, holder.headers)
            assert (response.status_code, problem(response)) == (
                401,
                "reauthentication-required",
            ), label

    assert checked >= 1
