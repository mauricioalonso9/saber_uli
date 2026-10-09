"""T137: administración de cuentas por API (FR-023 a FR-026, FR-029, FR-030; SC-004)."""

from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.catalog import ProgramFactory
from tests.integration.identity.staff import StaffFactory

USERS = "/api/v1/admin/users"


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


async def audit(engine: AsyncEngine, user_id: UUID) -> list[tuple[str, Any, dict[str, Any]]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT action, actor_id, details FROM identity.audit_events
                   WHERE subject_user_id = :u AND action LIKE 'user.%'
                   ORDER BY occurred_at, id"""
            ),
            {"u": user_id},
        )
        return [(row.action, row.actor_id, row.details) for row in rows]


async def test_listar_y_filtrar_cuentas(
    api_client: httpx.AsyncClient, staff: StaffFactory, committed_login: CommittedLogin
) -> None:
    admin = await staff(Role.ADMIN)
    teacher, _ = await committed_login(Role.TEACHER)
    guest, _ = await committed_login(guest=True)

    by_email = await api_client.get(USERS, params={"q": teacher.email[:14]}, headers=admin.headers)
    by_role = await api_client.get(
        USERS, params={"role": "teacher", "page_size": 100}, headers=admin.headers
    )
    by_kind = await api_client.get(
        USERS, params={"kind": "guest", "status": "active", "page_size": 100}, headers=admin.headers
    )

    assert by_email.status_code == 200, by_email.text
    found = {item["id"]: item for item in by_email.json()["items"]}
    item = found[str(teacher.id)]
    assert {"id", "kind", "status", "roles", "created_at", "email", "display_name"} <= set(item)
    assert sorted(item["roles"]) == ["student", "teacher"]
    assert str(teacher.id) in {i["id"] for i in by_role.json()["items"]}
    guests = {i["id"]: i for i in by_kind.json()["items"]}
    assert str(guest.id) in guests and str(teacher.id) not in guests
    assert {"page", "page_size", "total"} <= set(by_kind.json())


async def test_obtener_una_cuenta_y_404_si_no_existe(
    api_client: httpx.AsyncClient, staff: StaffFactory, committed_login: CommittedLogin
) -> None:
    admin = await staff(Role.ADMIN)
    student, _ = await committed_login()

    found = await api_client.get(f"{USERS}/{student.id}", headers=admin.headers)
    missing = await api_client.get(f"{USERS}/{uuid4()}", headers=admin.headers)

    assert found.status_code == 200
    assert (found.json()["id"], found.json()["status"]) == (str(student.id), "active")
    assert missing.status_code == 404


async def test_desactivar_termina_las_sesiones_y_reactivar_lo_permite_de_nuevo(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    committed_login: CommittedLogin,
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)
    student, token = await committed_login()
    student_headers = {"Authorization": f"Bearer {token}"}
    assert (await api_client.get("/api/v1/me", headers=student_headers)).status_code == 200

    disabled = await api_client.patch(
        f"{USERS}/{student.id}", json={"status": "disabled"}, headers=admin.headers
    )

    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"
    after = await api_client.get("/api/v1/me", headers=student_headers)
    assert after.status_code == 401
    assert problem_type(after) == "account-disabled"

    reactivated = await api_client.patch(
        f"{USERS}/{student.id}", json={"status": "active"}, headers=admin.headers
    )
    assert reactivated.json()["status"] == "active"
    assert [(action, actor) for action, actor, _ in await audit(app_engine, student.id)] == [
        ("user.disabled", admin.id),
        ("user.reactivated", admin.id),
    ]


async def test_definir_roles_y_programas_del_director_queda_auditado(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    committed_login: CommittedLogin,
    new_program: ProgramFactory,
    app_engine: AsyncEngine,
) -> None:
    admin = await staff(Role.ADMIN)
    teacher, _ = await committed_login(Role.TEACHER)
    program = await new_program()

    response = await api_client.put(
        f"{USERS}/{teacher.id}/roles",
        json={"roles": ["student", "program_director"], "director_program_ids": [str(program)]},
        headers=admin.headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert sorted(body["roles"]) == ["program_director", "student"]
    assert [p["id"] for p in body["director_programs"]] == [str(program)]
    entries = {action: details for action, _, details in await audit(app_engine, teacher.id)}
    assert entries["user.role_granted"] == {
        "roles": ["program_director"],
        "before": ["student", "teacher"],
        "after": ["program_director", "student"],
    }
    assert entries["user.role_revoked"]["roles"] == ["teacher"]
    assert entries["user.director_programs_changed"] == {"program_ids": [str(program)]}


async def test_retirar_un_rol_cierra_las_sesiones(
    api_client: httpx.AsyncClient, staff: StaffFactory, committed_login: CommittedLogin
) -> None:
    admin = await staff(Role.ADMIN)
    teacher, token = await committed_login(Role.TEACHER)

    await api_client.put(
        f"{USERS}/{teacher.id}/roles", json={"roles": ["student"]}, headers=admin.headers
    )

    after = await api_client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert after.status_code == 401


async def test_reglas_de_roles_responden_409(
    api_client: httpx.AsyncClient, staff: StaffFactory, committed_login: CommittedLogin
) -> None:
    admin = await staff(Role.ADMIN)
    student, _ = await committed_login()
    guest, _ = await committed_login(guest=True)
    path = f"{USERS}/{student.id}/roles"

    cases = [
        (path, {"roles": ["teacher"]}, "student-role-required"),
        (path, {"roles": ["student", "program_director"]}, "director-requires-programs"),
        (path, {"roles": ["student", "guest"]}, "guest-role-exclusive"),
        (f"{USERS}/{guest.id}/roles", {"roles": ["guest", "teacher"]}, "guest-role-exclusive"),
        (f"{USERS}/{admin.id}/roles", {"roles": ["student"]}, "last-admin"),
    ]
    for url, body, slug in cases:
        response = await api_client.put(url, json=body, headers=admin.headers)
        assert response.status_code == 409, (body, response.text)
        assert problem_type(response) == slug

    own = await api_client.patch(
        f"{USERS}/{admin.id}", json={"status": "disabled"}, headers=admin.headers
    )
    assert own.status_code == 409
    assert problem_type(own) == "last-admin"


async def test_solo_administradores_con_sesion_privilegiada(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    teacher = await staff(Role.TEACHER)
    admin_without_priv = await staff(Role.ADMIN, priv=False)

    forbidden = await api_client.get(USERS, headers=teacher.headers)
    reauth = await api_client.get(USERS, headers=admin_without_priv.headers)

    assert forbidden.status_code == 403
    assert reauth.status_code == 401
    assert problem_type(reauth) == "reauthentication-required"
