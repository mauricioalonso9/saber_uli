"""T166: exportación de «Mis datos» (FR-031; escenarios 8.1 y 8.2; research R-26).

`GET /api/v1/me/data-export` descarga un JSON (`Content-Disposition: attachment`) con identidad,
perfil, roles, nombres de grupos, historial de autorizaciones, invitación (solo invitados) y la
nota de cómo corregir los datos del directorio. Nunca incluye datos de otras personas. Los demás
contextos agregan sus secciones con el registro de proveedores.
"""

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.application.data_export import DataExport
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.data_export_registry import DataExportRegistry
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import CommittedLogin
from tests.integration.identity.catalog import ProgramFactory
from tests.integration.identity.guests import Guests
from tests.integration.identity.staff import StaffFactory, accept_current_policy

EXPORT = "/api/v1/me/data-export"


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> Any:
    async with engine.begin() as conn:
        result = await conn.execute(text(statement), params)
        return result.scalar_one_or_none() if result.returns_rows else None


async def group_with(engine: AsyncEngine, owner: UUID, name: str, *members: UUID) -> UUID:
    group_id = await sql(
        engine,
        "INSERT INTO identity.groups (name, created_by) VALUES (:n, :o) RETURNING id",
        n=name,
        o=owner,
    )
    for member in members:
        await sql(
            engine,
            "INSERT INTO identity.group_members (group_id, user_id) VALUES (:g, :u)",
            g=group_id,
            u=member,
        )
    return UUID(str(group_id))


async def test_descarga_todos_los_datos_del_institucional(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    committed_login: CommittedLogin,
    new_program: ProgramFactory,
    app_engine: AsyncEngine,
) -> None:
    me = await staff(Role.TEACHER)
    owner = await staff(Role.ADMIN)
    classmate, _ = await committed_login()
    assert classmate.id is not None
    classmate_name = f"Compañera {uuid4().hex[:6]}"
    await sql(
        app_engine,
        "UPDATE identity.users SET display_name = :n WHERE id = :u",
        n=classmate_name,
        u=classmate.id,
    )
    program = await new_program(name="Derecho")
    await sql(
        app_engine,
        """INSERT INTO identity.profiles (user_id, program_id, semester, daily_goal)
           VALUES (:u, :p, 7, 'intense')""",
        u=me.id,
        p=program,
    )
    await group_with(app_engine, owner.id, "Grupo de Mis Datos", me.id, classmate.id)
    await group_with(app_engine, owner.id, "Grupo ajeno", classmate.id)

    response = await api_client.get(EXPORT, headers=me.headers)

    assert response.status_code == 200, response.text
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert 'filename="saber-uli-mis-datos-' in disposition
    assert disposition.endswith('.json"')
    data = response.json()
    assert set(data) >= {"generated_at", "identity", "profile", "roles", "groups", "consents"}
    identity = data["identity"]
    assert identity["id"] == str(me.id)
    assert identity["kind"] == "institutional"
    assert identity["display_name"] == me.display_name
    assert identity["email"].endswith("@unilibre.edu.co")
    assert "directorio" in identity["source_note"]
    assert sorted(data["roles"]) == ["student", "teacher"]
    assert data["profile"]["program"]["name"] == "Derecho"
    assert (data["profile"]["semester"], data["profile"]["daily_goal"]) == (7, "intense")
    assert data["groups"] == ["Grupo de Mis Datos"]
    assert [c["decision"] for c in data["consents"]] == ["accepted"]
    assert "invitation" not in data
    # Nada de otras personas: ni el nombre de la compañera ni quién creó el grupo.
    assert classmate_name not in response.text
    assert str(classmate.id) not in response.text
    assert str(owner.id) not in response.text


async def test_el_invitado_ve_su_invitacion_sin_datos_de_quien_lo_invito(
    api_client: httpx.AsyncClient,
    committed_login: CommittedLogin,
    guests: Guests,
    app_engine: AsyncEngine,
) -> None:
    teacher, _ = await committed_login(Role.TEACHER)
    guest, token = await committed_login(guest=True)
    assert guest.id is not None and teacher.id is not None and teacher.email is not None
    await accept_current_policy(app_engine, guest.id)
    await guests.invitation(
        teacher.id, email=guest.email, status="accepted", guest_user_id=guest.id, access_days=20
    )

    response = await api_client.get(EXPORT, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["identity"]["kind"] == "guest"
    assert data["roles"] == ["guest"]
    assert set(data["invitation"]) == {"accepted_at", "access_expires_at"}
    assert "invitación" in data["identity"]["source_note"]
    assert teacher.email not in response.text
    assert str(teacher.id) not in response.text


async def test_exige_la_autorizacion_de_datos_vigente(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()

    response = await api_client.get(EXPORT, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["type"].endswith("consent-required")


async def test_requiere_sesion(api_client: httpx.AsyncClient) -> None:
    assert (await api_client.get(EXPORT)).status_code == 401


class ProgressProvider:
    """Un contexto futuro (por ejemplo, el progreso de 002) que agrega su sección."""

    section = "progress"

    def __init__(self) -> None:
        self.asked: list[UUID] = []

    async def export(self, user_id: UUID) -> Mapping[str, Any]:
        self.asked.append(user_id)
        return {"xp": 120, "lessons": 3}


async def test_los_demas_contextos_agregan_secciones(
    committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    user, _ = await committed_login()
    assert user.id is not None
    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    registry = DataExportRegistry()
    provider = ProgressProvider()
    registry.register(provider)
    export = DataExport(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
        clock=SystemClock(),
        registry=registry,
    )

    result = await export.execute(user.id)

    assert provider.asked == [user.id]
    assert result.sections == {"progress": {"xp": 120, "lessons": 3}}


def test_el_registro_no_admite_secciones_repetidas() -> None:
    registry = DataExportRegistry()
    registry.register(ProgressProvider())
    with pytest.raises(ValueError, match="progress"):
        registry.register(ProgressProvider())
