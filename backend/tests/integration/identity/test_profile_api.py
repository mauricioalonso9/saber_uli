"""T096: perfil y catálogo de programas por API (FR-019 a FR-022; escenarios 3.1 a 3.4).

`GET /api/v1/programs`, `GET /api/v1/me/profile` y `PUT /api/v1/me/profile`.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.domain.user import User
from tests.integration.conftest import CommittedLogin

ProgramFactory = Callable[..., Awaitable[UUID]]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


@pytest.fixture
async def program(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[ProgramFactory]:
    created: list[UUID] = []

    async def create(*, active: bool = True, name: str = "Derecho") -> UUID:
        async with app_engine.begin() as conn:
            program_id = (
                await conn.execute(
                    text(
                        """INSERT INTO identity.programs (code, name, campus, active)
                           VALUES (:code, :name, 'Bogotá', :active) RETURNING id"""
                    ),
                    {"code": f"T-{uuid4().hex[:8].upper()}", "name": name, "active": active},
                )
            ).scalar_one()
        created.append(program_id)
        return UUID(str(program_id))

    yield create
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM identity.profiles WHERE program_id = ANY(:ids)"), {"ids": created}
        )
        await conn.execute(
            text("DELETE FROM identity.programs WHERE id = ANY(:ids)"), {"ids": created}
        )
    await engine.dispose()


@pytest.fixture
def consented(app_engine: AsyncEngine) -> Callable[[User], Awaitable[None]]:
    """Registra la aceptación de la política vigente (requisito de FR-014)."""

    async def accept(user: User) -> None:
        async with app_engine.begin() as conn:
            await conn.execute(
                text(
                    """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
                       SELECT :u, id, 'accepted', 'web_pwa' FROM identity.policy_versions
                       WHERE effective_from <= now()
                       ORDER BY effective_from DESC, created_at DESC LIMIT 1"""
                ),
                {"u": user.id},
            )

    return accept


@pytest.fixture
def login(
    committed_login: CommittedLogin, consented: Callable[[User], Awaitable[None]]
) -> Callable[..., Awaitable[tuple[User, str]]]:
    async def create(*, guest: bool = False) -> tuple[User, str]:
        user, token = await committed_login(guest=guest)
        await consented(user)
        return user, token

    return create


async def put_profile(
    client: httpx.AsyncClient, token: str, body: dict[str, Any]
) -> httpx.Response:
    return await client.put("/api/v1/me/profile", json=body, headers=bearer(token))


async def me(client: httpx.AsyncClient, token: str) -> dict[str, Any]:
    response = await client.get("/api/v1/me", headers=bearer(token))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def institutional(program_id: UUID, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "program_id": str(program_id),
        "semester": 8,
        "expected_exam_date": "2027-05-30",
        "daily_goal": "regular",
    }
    body.update(overrides)
    return body


# ------------------------------------------------------------------- autorización (FR-014)


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/api/v1/programs"), ("GET", "/api/v1/me/profile"), ("PUT", "/api/v1/me/profile")],
)
async def test_sin_autorizacion_de_datos_responde_403(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, method: str, path: str
) -> None:
    _, token = await committed_login()

    response = await api_client.request(
        method, path, json={"daily_goal": "regular"}, headers=bearer(token)
    )

    assert response.status_code == 403
    assert problem_type(response) == "consent-required"


# ------------------------------------------------------------------- programas


async def test_el_catalogo_lista_solo_programas_activos(
    api_client: httpx.AsyncClient, login: Any, program: ProgramFactory
) -> None:
    active = await program(name="Contaduría Pública")
    inactive = await program(active=False)
    _, token = await login()

    response = await api_client.get("/api/v1/programs", headers=bearer(token))

    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()}
    assert str(inactive) not in by_id
    assert set(by_id[str(active)]) == {"id", "code", "name", "campus", "active"}
    assert by_id[str(active)]["name"] == "Contaduría Pública"
    assert all(item["active"] for item in by_id.values())


# ------------------------------------------------------------------- institucional


async def test_un_perfil_nuevo_esta_incompleto(api_client: httpx.AsyncClient, login: Any) -> None:
    _, token = await login()

    response = await api_client.get("/api/v1/me/profile", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["complete"] is False
    assert (await me(api_client, token))["onboarding"]["profile_required"] is True


async def test_completar_el_perfil_institucional_termina_el_primer_ingreso(
    api_client: httpx.AsyncClient, login: Any, program: ProgramFactory, app_engine: AsyncEngine
) -> None:
    user, token = await login()
    program_id = await program()

    response = await put_profile(api_client, token, institutional(program_id))

    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["complete"] is True
    assert profile["program"]["id"] == str(program_id)
    assert (profile["semester"], profile["expected_exam_date"]) == (8, "2027-05-30")
    assert profile["daily_goal"] == "regular"
    assert "guest_display_name" not in profile
    assert (await me(api_client, token))["onboarding"]["profile_required"] is False
    got = await api_client.get("/api/v1/me/profile", headers=bearer(token))
    assert got.json() == profile
    async with app_engine.connect() as conn:
        completed = (
            await conn.execute(
                text("SELECT onboarding_completed_at FROM identity.users WHERE id = :u"),
                {"u": user.id},
            )
        ).scalar_one()
    assert completed is not None


async def test_editar_el_perfil_no_cambia_la_fecha_del_primer_ingreso(
    api_client: httpx.AsyncClient, login: Any, program: ProgramFactory, app_engine: AsyncEngine
) -> None:
    user, token = await login()
    program_id = await program()
    await put_profile(api_client, token, institutional(program_id))

    async def completed_at() -> Any:
        async with app_engine.connect() as conn:
            return (
                await conn.execute(
                    text("SELECT onboarding_completed_at FROM identity.users WHERE id = :u"),
                    {"u": user.id},
                )
            ).scalar_one()

    first = await completed_at()

    response = await put_profile(
        api_client, token, institutional(program_id, semester=9, daily_goal="intense")
    )

    assert response.status_code == 200
    assert (response.json()["semester"], response.json()["daily_goal"]) == (9, "intense")
    assert await completed_at() == first


@pytest.mark.parametrize(
    "extra",
    [{"display_name": "Otro nombre"}, {"email": "otro@unilibre.edu.co"}],
    ids=["nombre", "correo"],
)
async def test_nombre_y_correo_institucionales_no_son_editables(
    api_client: httpx.AsyncClient,
    login: Any,
    program: ProgramFactory,
    extra: dict[str, str],
) -> None:
    user, token = await login()
    program_id = await program()

    response = await put_profile(api_client, token, {**institutional(program_id), **extra})

    assert response.status_code == 422
    data = await me(api_client, token)
    assert (data["display_name"], data["email"]) == (user.display_name, user.email)


async def test_institucional_sin_semestre_responde_422(
    api_client: httpx.AsyncClient, login: Any, program: ProgramFactory
) -> None:
    _, token = await login()
    body = institutional(await program())
    del body["semester"]

    response = await put_profile(api_client, token, body)

    assert response.status_code == 422
    assert problem_type(response) == "invalid-profile"


@pytest.mark.parametrize("which", ["inactivo", "inexistente"])
async def test_un_programa_no_disponible_responde_422(
    api_client: httpx.AsyncClient, login: Any, program: ProgramFactory, which: str
) -> None:
    _, token = await login()
    program_id = await program(active=False) if which == "inactivo" else uuid4()

    response = await put_profile(api_client, token, institutional(program_id))

    assert response.status_code == 422
    assert problem_type(response) == "program-not-available"


# ------------------------------------------------------------------- invitado


async def test_el_invitado_completa_nombre_y_meta_y_ese_es_su_nombre_visible(
    api_client: httpx.AsyncClient, login: Any
) -> None:
    _, token = await login(guest=True)

    response = await put_profile(
        api_client, token, {"guest_display_name": "Laura Gómez", "daily_goal": "casual"}
    )

    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["complete"] is True
    assert profile["guest_display_name"] == "Laura Gómez"
    assert "program" not in profile
    data = await me(api_client, token)
    assert data["display_name"] == "Laura Gómez"
    assert data["onboarding"]["profile_required"] is False


async def test_el_invitado_no_indica_programa(
    api_client: httpx.AsyncClient, login: Any, program: ProgramFactory
) -> None:
    _, token = await login(guest=True)

    response = await put_profile(
        api_client,
        token,
        {"guest_display_name": "Laura", "daily_goal": "casual", "program_id": str(await program())},
    )

    assert response.status_code == 422
    assert problem_type(response) == "invalid-profile"
