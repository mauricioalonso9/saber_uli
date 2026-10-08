"""T154: solicitud de supresión por API (FR-032, FR-034, FR-034d; escenarios 7.1, 7.2, 7.4, 7.5).

- `POST /api/v1/me/deletion-request` exige escribir `ELIMINAR`; responde 202, la cuenta pasa a
  `deletion_pending`, `auth_epoch` + 1 y la siguiente petición responde 401.
- La fecha límite es la fecha de la solicitud más 15 días hábiles en Colombia.
- No exige la autorización de datos vigente (`x-consent-exempt`).
- El último administrador activo recibe 409 `last-admin` y su cuenta no cambia.
- Una segunda solicitud en curso → 409 `deletion-already-requested`.
- `GET /api/v1/admin/deletion-requests` lista estado y fecha límite, con filtro de estado.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.application.deletion import (
    DeletionAlreadyRequestedError,
    DeletionService,
)
from saber_uli.identity.domain.business_days import deletion_due_date
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.staff import StaffFactory

MINE = "/api/v1/me/deletion-request"
ADMIN = "/api/v1/admin/deletion-requests"
CONFIRM = {"confirmation": "ELIMINAR"}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


async def account(engine: AsyncEngine, user_id: UUID) -> Any:
    async with engine.connect() as conn:
        return (
            await conn.execute(
                text("SELECT status, auth_epoch FROM identity.users WHERE id = :u"),
                {"u": user_id},
            )
        ).one()


async def open_sessions(engine: AsyncEngine, user_id: UUID) -> int:
    async with engine.connect() as conn:
        value: int = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM identity.sessions"
                    " WHERE user_id = :u AND revoked_at IS NULL"
                ),
                {"u": user_id},
            )
        ).scalar_one()
    return value


async def audit(engine: AsyncEngine, user_id: UUID) -> list[Any]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT action, actor_id, target_type, target_id, details
                   FROM identity.audit_events
                   WHERE subject_user_id = :u AND action LIKE 'deletion.%'
                   ORDER BY occurred_at, id"""
            ),
            {"u": user_id},
        )
        return list(rows)


@pytest.fixture
def service(app_engine: AsyncEngine) -> DeletionService:
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    return DeletionService(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
        clock=SystemClock(),
    )


async def test_exige_escribir_eliminar(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    user, token = await committed_login()
    assert user.id is not None

    for body in ({}, {"confirmation": "eliminar"}, {"confirmation": "SI"}):
        response = await api_client.post(MINE, json=body, headers=bearer(token))
        assert response.status_code == 422, (body, response.text)

    assert (await account(app_engine, user.id)).status == "active"


async def test_solicitar_termina_el_acceso_de_inmediato(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    # Sin autorización de datos vigente: la ruta está exenta (FR-014, escenario 7.1).
    user, token = await committed_login()
    assert user.id is not None
    before = await account(app_engine, user.id)

    assert (await api_client.get(MINE, headers=bearer(token))).status_code == 404
    response = await api_client.post(MINE, json=CONFIRM, headers=bearer(token))

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "received"
    assert body["origin"] == "user_request"
    requested_at = datetime.fromisoformat(body["requested_at"])
    assert date.fromisoformat(body["due_date"]) == deletion_due_date(requested_at)
    assert "user_id" not in body  # solo en las vistas de administrador

    after = await account(app_engine, user.id)
    assert after.status == "deletion_pending"
    assert after.auth_epoch == before.auth_epoch + 1
    assert await open_sessions(app_engine, user.id) == 0
    assert (await api_client.get("/api/v1/me", headers=bearer(token))).status_code == 401

    (entry,) = await audit(app_engine, user.id)
    assert entry.action == "deletion.requested"
    assert entry.actor_id == user.id
    assert (entry.target_type, str(entry.target_id)) == ("deletion_request", body["id"])
    assert entry.details == {"origin": "user_request", "due_date": body["due_date"]}


async def test_una_segunda_solicitud_en_curso_responde_409(
    service: DeletionService, committed_login: CommittedLogin
) -> None:
    user, _ = await committed_login()
    assert user.id is not None

    first = await service.request(user.id)
    with pytest.raises(DeletionAlreadyRequestedError) as raised:
        await service.request(user.id)

    assert raised.value.slug == "deletion-already-requested"
    assert first.status.value == "received"


async def test_el_ultimo_administrador_activo_no_puede_solicitarla(
    api_client: httpx.AsyncClient, staff: StaffFactory, app_engine: AsyncEngine
) -> None:
    admin = await staff(Role.ADMIN)
    before = await account(app_engine, admin.id)

    response = await api_client.post(MINE, json=CONFIRM, headers=admin.headers)

    assert response.status_code == 409, response.text
    assert problem_type(response) == "last-admin"
    assert "Administrador" in response.json()["detail"]
    assert await account(app_engine, admin.id) == before
    assert await audit(app_engine, admin.id) == []
    assert (await api_client.get("/api/v1/me", headers=admin.headers)).status_code == 200


async def test_un_administrador_puede_solicitarla_si_hay_otro(
    api_client: httpx.AsyncClient, staff: StaffFactory, app_engine: AsyncEngine
) -> None:
    await staff(Role.ADMIN)
    leaving = await staff(Role.ADMIN)

    response = await api_client.post(MINE, json=CONFIRM, headers=leaving.headers)

    assert response.status_code == 202, response.text
    assert (await account(app_engine, leaving.id)).status == "deletion_pending"


async def test_el_administrador_ve_estado_y_fecha_limite(
    api_client: httpx.AsyncClient, staff: StaffFactory, committed_login: CommittedLogin
) -> None:
    admin = await staff(Role.ADMIN)
    user, token = await committed_login()
    created = (await api_client.post(MINE, json=CONFIRM, headers=bearer(token))).json()

    listed = await api_client.get(
        ADMIN, params={"status": "received", "page_size": 100}, headers=admin.headers
    )
    completed = await api_client.get(ADMIN, params={"status": "completed"}, headers=admin.headers)

    assert listed.status_code == 200, listed.text
    items = {item["id"]: item for item in listed.json()["items"]}
    item = items[created["id"]]
    assert item["user_id"] == str(user.id)
    assert (item["status"], item["origin"], item["due_date"]) == (
        "received",
        "user_request",
        created["due_date"],
    )
    assert {"page", "page_size", "total"} <= set(listed.json())
    assert created["id"] not in {i["id"] for i in completed.json()["items"]}
    # Sin datos personales en el listado.
    assert "@" not in listed.text


async def test_solo_administradores_con_sesion_privilegiada(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    teacher = await staff(Role.TEACHER)
    admin = await staff(Role.ADMIN, priv=False)

    assert (await api_client.get(ADMIN, headers=teacher.headers)).status_code == 403
    response = await api_client.get(ADMIN, headers=admin.headers)
    assert response.status_code == 401
    assert problem_type(response) == "reauthentication-required"


async def test_requiere_sesion(api_client: httpx.AsyncClient) -> None:
    assert (await api_client.post(MINE, json=CONFIRM)).status_code == 401
    assert (await api_client.get(MINE)).status_code == 401

