"""T139: lo que ven docentes y directores de programa (FR-026, FR-027, FR-030).

- Un docente solo ve sus grupos y, de sus estudiantes, el nombre (nunca el correo).
- Un grupo ajeno responde 404, como si no existiera.
- Un usuario que solo es Director de programa no accede a vistas con nombres o correos.
- La fachada `director_program_ids` devuelve los programas de un director (para la analítica).
"""

from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.application.directory import IdentityDirectory
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.catalog import ProgramFactory
from tests.integration.identity.staff import Staff, StaffFactory

TEACHER_GROUPS = "/api/v1/teacher/groups"


async def group_with(
    client: httpx.AsyncClient,
    admin: Staff,
    *,
    name: str,
    members: list[UUID],
    teachers: list[UUID],
) -> dict[str, Any]:
    created = await client.post("/api/v1/admin/groups", json={"name": name}, headers=admin.headers)
    assert created.status_code == 201, created.text
    group: dict[str, Any] = created.json()
    if members:
        await client.post(
            f"/api/v1/admin/groups/{group['id']}/members",
            json={"user_ids": [str(m) for m in members]},
            headers=admin.headers,
        )
    if teachers:
        await client.post(
            f"/api/v1/admin/groups/{group['id']}/teachers",
            json={"user_ids": [str(t) for t in teachers]},
            headers=admin.headers,
        )
    return group


@pytest.fixture
async def world(
    api_client: httpx.AsyncClient, staff: StaffFactory, committed_login: CommittedLogin
) -> dict[str, Any]:
    admin = await staff(Role.ADMIN)
    teacher = await staff(Role.TEACHER)
    other_teacher = await staff(Role.TEACHER)
    ana, _ = await committed_login()
    pedro, _ = await committed_login()
    assert ana.id is not None and pedro.id is not None
    mine = await group_with(
        api_client, admin, name="Mi grupo", members=[ana.id, pedro.id], teachers=[teacher.id]
    )
    theirs = await group_with(
        api_client, admin, name="Grupo ajeno", members=[pedro.id], teachers=[other_teacher.id]
    )
    return {"teacher": teacher, "mine": mine, "theirs": theirs, "ana": ana, "pedro": pedro}


async def test_el_docente_solo_ve_sus_grupos(
    api_client: httpx.AsyncClient, world: dict[str, Any]
) -> None:
    response = await api_client.get(TEACHER_GROUPS, headers=world["teacher"].headers)

    assert response.status_code == 200, response.text
    groups = response.json()
    assert [g["id"] for g in groups] == [world["mine"]["id"]]
    assert groups[0]["member_count"] == 2
    assert set(groups[0]) <= {"id", "name", "cohort_label", "program_id", "member_count"}


async def test_de_sus_estudiantes_solo_ve_el_nombre(
    api_client: httpx.AsyncClient, world: dict[str, Any]
) -> None:
    response = await api_client.get(
        f"{TEACHER_GROUPS}/{world['mine']['id']}/students", headers=world["teacher"].headers
    )

    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 2
    students = {item["user_id"]: item for item in page["items"]}
    assert set(students) == {str(world["ana"].id), str(world["pedro"].id)}
    for item in page["items"]:
        assert "email" not in item
        assert set(item) <= {"user_id", "display_name", "progress"}
    assert world["ana"].email not in response.text
    assert world["pedro"].email not in response.text


async def test_un_grupo_ajeno_responde_404(
    api_client: httpx.AsyncClient, world: dict[str, Any]
) -> None:
    response = await api_client.get(
        f"{TEACHER_GROUPS}/{world['theirs']['id']}/students", headers=world["teacher"].headers
    )

    assert response.status_code == 404


async def test_un_director_sin_rol_docente_no_ve_nombres(
    api_client: httpx.AsyncClient, staff: StaffFactory, world: dict[str, Any]
) -> None:
    # Solo Director de programa (y Estudiante, que todo institucional conserva).
    director = await staff(Role.PROGRAM_DIRECTOR)

    for path in (
        TEACHER_GROUPS,
        f"{TEACHER_GROUPS}/{world['mine']['id']}/students",
        "/api/v1/admin/users",
        "/api/v1/invitations",
    ):
        response = await api_client.get(path, headers=director.headers)
        assert response.status_code == 403, path


async def test_la_fachada_devuelve_los_programas_del_director(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    committed_login: CommittedLogin,
    new_program: ProgramFactory,
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)
    person, _ = await committed_login()
    first, second = await new_program(), await new_program(name="Contaduría")
    await api_client.put(
        f"/api/v1/admin/users/{person.id}/roles",
        json={
            "roles": ["student", "program_director"],
            "director_program_ids": [str(first), str(second)],
        },
        headers=admin.headers,
    )
    session_factory = create_session_factory(app_engine)
    directory = IdentityDirectory(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, EventBus())
    )
    assert person.id is not None

    assert await directory.director_program_ids(person.id) == {first, second}
    assert await directory.director_program_ids(admin.id) == set()
