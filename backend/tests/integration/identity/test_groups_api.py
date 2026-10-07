"""T138: grupos por API (FR-027; SC-004)."""

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.staff import Staff, StaffFactory

GROUPS = "/api/v1/admin/groups"


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


async def create(client: httpx.AsyncClient, admin: Staff, **body: Any) -> dict[str, Any]:
    response = await client.post(
        GROUPS, json={"name": "Derecho 2026-2", **body}, headers=admin.headers
    )
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def actions(engine: AsyncEngine, group_id: str) -> list[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT action FROM identity.audit_events WHERE target_id = :g"
                " ORDER BY occurred_at, id"
            ),
            {"g": group_id},
        )
        return [row.action for row in rows]


async def test_crear_obtener_listar_editar_y_archivar(
    api_client: httpx.AsyncClient, staff: StaffFactory, app_engine: AsyncEngine
) -> None:
    admin = await staff(Role.ADMIN)
    group = await create(api_client, admin, cohort_label="2026-2", description="Cohorte")

    assert {"id", "name", "member_count", "teachers", "created_at"} <= set(group)
    assert (group["member_count"], group["teachers"]) == (0, [])
    fetched = await api_client.get(f"{GROUPS}/{group['id']}", headers=admin.headers)
    assert fetched.json() == group
    listed = await api_client.get(GROUPS, params={"q": "derecho 2026"}, headers=admin.headers)
    assert group["id"] in {item["id"] for item in listed.json()["items"]}

    renamed = await api_client.patch(
        f"{GROUPS}/{group['id']}", json={"name": "Derecho 2027-1"}, headers=admin.headers
    )
    archived = await api_client.patch(
        f"{GROUPS}/{group['id']}", json={"archived": True}, headers=admin.headers
    )

    assert renamed.json()["name"] == "Derecho 2027-1"
    assert archived.json()["archived_at"]
    assert await actions(app_engine, group["id"]) == [
        "group.created",
        "group.updated",
        "group.archived",
    ]


async def test_miembros_solo_estudiantes_institucionales(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    committed_login: CommittedLogin,
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)
    group = await create(api_client, admin)
    a, _ = await committed_login()
    b, _ = await committed_login()
    guest, _ = await committed_login(guest=True)
    members = f"{GROUPS}/{group['id']}/members"

    added = await api_client.post(
        members, json={"user_ids": [str(a.id), str(b.id)]}, headers=admin.headers
    )
    rejected = await api_client.post(
        members, json={"user_ids": [str(guest.id)]}, headers=admin.headers
    )
    removed = await api_client.delete(f"{members}/{a.id}", headers=admin.headers)

    assert added.status_code == 200, added.text
    assert added.json()["member_count"] == 2
    assert rejected.status_code == 409
    assert problem_type(rejected) == "not-institutional-student"
    assert removed.status_code == 204
    fetched = await api_client.get(f"{GROUPS}/{group['id']}", headers=admin.headers)
    assert fetched.json()["member_count"] == 1
    log = await actions(app_engine, group["id"])
    assert log.count("group.member_added") == 2
    assert log.count("group.member_removed") == 1


async def test_docentes_solo_con_rol_docente(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    committed_login: CommittedLogin,
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)
    group = await create(api_client, admin)
    teacher, _ = await committed_login(Role.TEACHER)
    student, _ = await committed_login()
    teachers = f"{GROUPS}/{group['id']}/teachers"

    added = await api_client.post(
        teachers, json={"user_ids": [str(teacher.id)]}, headers=admin.headers
    )
    rejected = await api_client.post(
        teachers, json={"user_ids": [str(student.id)]}, headers=admin.headers
    )

    assert added.status_code == 200, added.text
    assert added.json()["teachers"] == [
        {"id": str(teacher.id), "display_name": teacher.display_name}
    ]
    assert rejected.status_code == 409
    assert problem_type(rejected) == "not-a-teacher"
    assert (
        await api_client.delete(f"{teachers}/{teacher.id}", headers=admin.headers)
    ).status_code == 204
    log = await actions(app_engine, group["id"])
    assert {"group.teacher_added", "group.teacher_removed"} <= set(log)


async def test_un_grupo_inexistente_es_404_y_un_docente_no_administra(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    admin = await staff(Role.ADMIN)
    teacher = await staff(Role.TEACHER)
    missing = UUID("00000000-0000-7000-8000-00000000dead")

    assert (await api_client.get(f"{GROUPS}/{missing}", headers=admin.headers)).status_code == 404
    assert (await api_client.get(GROUPS, headers=teacher.headers)).status_code == 403
