"""T140: programas, parámetros y consulta de auditoría (FR-028, FR-006a, FR-035; SC-004)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.domain.roles import Role
from tests.integration.identity.staff import StaffFactory

PROGRAMS = "/api/v1/admin/programs"
SETTINGS = "/api/v1/admin/settings"
AUDIT = "/api/v1/admin/audit-events"


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


@pytest.fixture
async def created_programs(migrated_database: dict[str, str]) -> Any:
    codes: list[str] = []
    yield codes
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """DELETE FROM identity.audit_events WHERE target_id IN
                   (SELECT id FROM identity.programs WHERE code = ANY(:c))"""
            ),
            {"c": codes},
        )
        await conn.execute(text("DELETE FROM identity.programs WHERE code = ANY(:c)"), {"c": codes})
    await engine.dispose()


@pytest.fixture
async def restore_settings(migrated_database: dict[str, str]) -> Any:
    yield
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        for key, value in (
            ("teacher_max_access_days", 180),
            ("default_guest_access_days", 90),
            ("invitation_link_ttl_days", 7),
            ("sign_in_link_ttl_minutes", 15),
        ):
            await conn.execute(
                text(
                    "UPDATE identity.settings SET value = to_jsonb(CAST(:v AS integer)),"
                    " updated_by = NULL WHERE key = :k"
                ),
                {"k": key, "v": value},
            )
    await engine.dispose()


# ------------------------------------------------------------------- programas


async def test_crear_listar_y_editar_programas(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    created_programs: list[str],
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)
    code = f"T-{uuid4().hex[:6].upper()}"
    created_programs.append(code)

    created = await api_client.post(
        PROGRAMS, json={"code": code, "name": "Derecho", "campus": "Bogotá"}, headers=admin.headers
    )
    assert created.status_code == 201, created.text
    program = created.json()
    assert (program["code"], program["active"]) == (code, True)

    duplicated = await api_client.post(
        PROGRAMS, json={"code": code, "name": "Otro", "campus": "Cali"}, headers=admin.headers
    )
    assert duplicated.status_code == 409

    patched = await api_client.patch(
        f"{PROGRAMS}/{program['id']}",
        json={"name": "Derecho y Ciencias Políticas", "active": False},
        headers=admin.headers,
    )
    assert patched.status_code == 200, patched.text
    assert (patched.json()["name"], patched.json()["active"]) == (
        "Derecho y Ciencias Políticas",
        False,
    )
    listed = await api_client.get(PROGRAMS, params={"q": code}, headers=admin.headers)
    assert [item["id"] for item in listed.json()["items"]] == [program["id"]]
    async with app_engine.connect() as conn:
        actions = (
            (
                await conn.execute(
                    text(
                        "SELECT action FROM identity.audit_events WHERE target_id = :p"
                        " ORDER BY occurred_at, id"
                    ),
                    {"p": program["id"]},
                )
            )
            .scalars()
            .all()
        )
    assert actions == ["program.created", "program.updated"]


@pytest.mark.parametrize(
    "body",
    [
        {"code": "minúsculas", "name": "Derecho", "campus": "Bogotá"},
        {"code": "T-X1", "name": "De", "campus": "Bogotá"},
        {"code": "T-X2", "name": "Derecho", "campus": "B"},
    ],
    ids=["codigo", "nombre", "seccional"],
)
async def test_datos_de_programa_invalidos_responden_422(
    api_client: httpx.AsyncClient, staff: StaffFactory, body: dict[str, str]
) -> None:
    admin = await staff(Role.ADMIN)

    response = await api_client.post(PROGRAMS, json=body, headers=admin.headers)

    assert response.status_code == 422


# ------------------------------------------------------------------- parámetros


async def test_parametros_con_rangos_y_auditoria(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    restore_settings: None,
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)

    current = await api_client.get(SETTINGS, headers=admin.headers)
    changed = await api_client.patch(
        SETTINGS, json={"teacher_max_access_days": 120}, headers=admin.headers
    )
    out_of_range = await api_client.patch(
        SETTINGS, json={"sign_in_link_ttl_minutes": 4}, headers=admin.headers
    )

    assert current.json() == {
        "teacher_max_access_days": 180,
        "default_guest_access_days": 90,
        "invitation_link_ttl_days": 7,
        "sign_in_link_ttl_minutes": 15,
    }
    assert changed.status_code == 200, changed.text
    assert changed.json()["teacher_max_access_days"] == 120
    assert out_of_range.status_code == 422
    async with app_engine.connect() as conn:
        details = (
            (
                await conn.execute(
                    text(
                        "SELECT details FROM identity.audit_events"
                        " WHERE action = 'setting.changed' AND actor_id = :a"
                    ),
                    {"a": admin.id},
                )
            )
            .scalars()
            .all()
        )
    assert details == [{"key": "teacher_max_access_days", "before": 180, "after": 120}]


# ------------------------------------------------------------------- auditoría


async def test_consulta_de_auditoria_con_filtros_y_del_mas_reciente_al_mas_antiguo(
    api_client: httpx.AsyncClient, staff: StaffFactory, restore_settings: None
) -> None:
    admin = await staff(Role.ADMIN)
    since = datetime.now(UTC) - timedelta(seconds=1)
    for value in (100, 110):
        await api_client.patch(
            SETTINGS, json={"teacher_max_access_days": value}, headers=admin.headers
        )

    response = await api_client.get(
        AUDIT,
        params={
            "action": "setting.changed",
            "actor_id": str(admin.id),
            "from": since.isoformat(),
            "to": (datetime.now(UTC) + timedelta(seconds=5)).isoformat(),
        },
        headers=admin.headers,
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["details"]["after"] for item in items] == [110, 100]
    assert {"id", "occurred_at", "action", "target_type", "actor_id"} <= set(items[0])
    assert response.json()["total"] == 2

    empty = await api_client.get(
        AUDIT, params={"subject_user_id": str(uuid4())}, headers=admin.headers
    )
    assert empty.json()["items"] == []


async def test_la_auditoria_es_de_solo_lectura_y_solo_para_administradores(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    admin = await staff(Role.ADMIN)
    teacher = await staff(Role.TEACHER)

    assert (await api_client.post(AUDIT, json={}, headers=admin.headers)).status_code == 405
    assert (await api_client.get(AUDIT, headers=teacher.headers)).status_code == 403
    assert (await api_client.get(SETTINGS, headers=teacher.headers)).status_code == 403
