"""T085: autorización de datos y política por API (FR-014 a FR-018; escenarios 2.1 a 2.5).

`GET/POST /api/v1/me/consents`, `POST /api/v1/me/consents/revocation`,
`GET /api/v1/privacy-policy/current`, `GET /api/v1/privacy-policy/versions/{id}` y
`POST /api/v1/admin/privacy-policy/versions`.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import CommittedLogin

POLICY_FILE = Path(__file__).resolve().parents[3] / "seeds" / "politica_tratamiento_datos_v1.md"
CONSENT_KEYS = {"id", "policy_version_id", "policy_version", "decision", "channel", "decided_at"}
BODY = "Finalidad, datos recogidos, derechos y canales de atención. " * 5


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


@pytest.fixture
async def published(
    committed_login: CommittedLogin, migrated_database: dict[str, str]
) -> AsyncIterator[list[UUID]]:
    """Versiones publicadas por la prueba; se borran (con saber_migrator) antes que los usuarios."""
    ids: list[UUID] = []
    yield ids
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        for statement in (
            "DELETE FROM identity.consents WHERE policy_version_id = ANY(:ids)",
            "DELETE FROM identity.audit_events WHERE target_id = ANY(:ids)",
            "DELETE FROM identity.policy_versions WHERE id = ANY(:ids)",
        ):
            await conn.execute(text(statement), {"ids": ids})
    await engine.dispose()


async def current_policy(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get("/api/v1/privacy-policy/current")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def decide(
    client: httpx.AsyncClient, token: str, decision: str, version_id: str | None = None
) -> httpx.Response:
    if version_id is None:
        version_id = (await current_policy(client))["id"]
    return await client.post(
        "/api/v1/me/consents",
        json={"policy_version_id": version_id, "decision": decision},
        headers=bearer(token),
    )


async def consent_required(client: httpx.AsyncClient, token: str) -> bool:
    response = await client.get("/api/v1/me", headers=bearer(token))
    assert response.status_code == 200, response.text
    value: bool = response.json()["onboarding"]["consent_required"]
    return value


async def audit_actions(engine: AsyncEngine, user_id: UUID) -> list[tuple[str, str, Any]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT action, target_type, details FROM identity.audit_events
                   WHERE subject_user_id = :u AND action LIKE 'consent.%'
                   ORDER BY occurred_at, id"""
            ),
            {"u": user_id},
        )
        return [(row.action, row.target_type, row.details) for row in rows]


async def publish(
    client: httpx.AsyncClient, token: str, published: list[UUID], **overrides: Any
) -> httpx.Response:
    payload: dict[str, Any] = {
        "version": f"{uuid4().int % 10_000}.{uuid4().int % 10_000}",
        "title": "Política de tratamiento de datos personales",
        "body_markdown": BODY,
        "effective_from": datetime.now(UTC).isoformat(),
    }
    payload.update(overrides)
    response = await client.post(
        "/api/v1/admin/privacy-policy/versions", json=payload, headers=bearer(token)
    )
    if response.status_code == 201:
        published.append(UUID(response.json()["id"]))
    return response


# ------------------------------------------------------------------- política pública


async def test_la_politica_vigente_y_sus_versiones_no_exigen_sesion(
    api_client: httpx.AsyncClient,
) -> None:
    policy = await current_policy(api_client)

    assert set(policy) == {"id", "version", "title", "body_markdown", "effective_from"}
    assert policy["version"] == "1.0"
    assert policy["body_markdown"] == POLICY_FILE.read_text(encoding="utf-8")

    response = await api_client.get(f"/api/v1/privacy-policy/versions/{policy['id']}")
    assert response.status_code == 200
    assert response.json() == policy


async def test_una_version_inexistente_responde_404(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get(f"/api/v1/privacy-policy/versions/{uuid4()}")

    assert response.status_code == 404
    assert problem_type(response) == "not-found"


# ------------------------------------------------------------------- decidir


async def test_sin_decisiones_la_lista_esta_vacia(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()

    response = await api_client.get("/api/v1/me/consents", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {"current": None, "items": []}


async def test_aceptar_registra_usuario_fecha_version_decision_y_canal(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    user, token = await committed_login()
    policy = await current_policy(api_client)
    assert await consent_required(api_client, token) is True

    response = await decide(api_client, token, "accepted")

    assert response.status_code == 201, response.text
    consent = response.json()
    assert set(consent) == CONSENT_KEYS
    assert consent["policy_version_id"] == policy["id"]
    assert (consent["policy_version"], consent["decision"]) == ("1.0", "accepted")
    assert consent["channel"] == "web_pwa"
    assert datetime.fromisoformat(consent["decided_at"]).tzinfo is not None
    async with app_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT user_id, channel FROM identity.consents WHERE id = :id"),
                {"id": consent["id"]},
            )
        ).one()
    assert (row.user_id, row.channel) == (user.id, "web_pwa")

    listed = (await api_client.get("/api/v1/me/consents", headers=bearer(token))).json()
    assert listed == {"current": consent, "items": [consent]}
    assert await consent_required(api_client, token) is False
    assert await audit_actions(app_engine, user.id) == [
        ("consent.accepted", "policy", {"policy_version": "1.0"})
    ]


async def test_rechazar_queda_registrado_y_sigue_exigiendo_autorizacion(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    user, token = await committed_login()

    response = await decide(api_client, token, "rejected")

    assert response.status_code == 201, response.text
    assert response.json()["decision"] == "rejected"
    listed = (await api_client.get("/api/v1/me/consents", headers=bearer(token))).json()
    assert listed["current"] is None
    assert [item["decision"] for item in listed["items"]] == ["rejected"]
    assert await consent_required(api_client, token) is True
    assert [a for a, _, _ in await audit_actions(app_engine, user.id)] == ["consent.rejected"]


async def test_el_historial_va_del_mas_reciente_al_mas_antiguo(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()
    await decide(api_client, token, "rejected")
    await decide(api_client, token, "accepted")

    listed = (await api_client.get("/api/v1/me/consents", headers=bearer(token))).json()

    assert [item["decision"] for item in listed["items"]] == ["accepted", "rejected"]
    assert listed["current"] == listed["items"][0]


async def test_decidir_sobre_una_version_que_no_es_la_vigente_responde_409(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()

    response = await decide(api_client, token, "accepted", str(uuid4()))

    assert response.status_code == 409
    assert problem_type(response) == "policy-version-not-current"


async def test_revoked_no_es_una_decision_valida(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()

    response = await decide(api_client, token, "revoked")

    assert response.status_code == 422


async def test_decidir_exige_sesion(api_client: httpx.AsyncClient) -> None:
    policy = await current_policy(api_client)

    response = await api_client.post(
        "/api/v1/me/consents", json={"policy_version_id": policy["id"], "decision": "accepted"}
    )

    assert response.status_code == 401


# ------------------------------------------------------------------- revocar


async def test_revocar_sin_autorizacion_vigente_responde_409(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin
) -> None:
    _, token = await committed_login()
    await decide(api_client, token, "rejected")

    response = await api_client.post("/api/v1/me/consents/revocation", headers=bearer(token))

    assert response.status_code == 409
    assert problem_type(response) == "no-active-consent"


async def test_revocar_cierra_las_sesiones_y_la_siguiente_peticion_responde_401(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    user, token = await committed_login()
    await decide(api_client, token, "accepted")

    response = await api_client.post("/api/v1/me/consents/revocation", headers=bearer(token))

    assert response.status_code == 201, response.text
    assert response.json()["decision"] == "revoked"
    assert response.json()["policy_version"] == "1.0"
    assert (await api_client.get("/api/v1/me", headers=bearer(token))).status_code == 401
    async with app_engine.connect() as conn:
        epoch = (
            await conn.execute(
                text("SELECT auth_epoch FROM identity.users WHERE id = :u"), {"u": user.id}
            )
        ).scalar_one()
        open_sessions = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM identity.sessions"
                    " WHERE user_id = :u AND revoked_at IS NULL"
                ),
                {"u": user.id},
            )
        ).scalar_one()
    assert epoch == user.auth_epoch + 1
    assert open_sessions == 0
    assert [a for a, _, _ in await audit_actions(app_engine, user.id)] == [
        "consent.accepted",
        "consent.revoked",
    ]


# ------------------------------------------------------------------- publicar


async def staff_login(
    client: httpx.AsyncClient, committed_login: CommittedLogin, role: Role, *, priv: bool
) -> tuple[Any, str]:
    """Las rutas de administración también exigen autorización vigente (FR-014)."""
    user, token = await committed_login(role, priv=priv)
    assert (await decide(client, token, "accepted")).status_code == 201
    return user, token


async def test_publicar_exige_el_permiso(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, published: list[UUID]
) -> None:
    _, token = await staff_login(api_client, committed_login, Role.TEACHER, priv=True)

    response = await publish(api_client, token, published)

    assert response.status_code == 403
    assert problem_type(response) == "forbidden"


async def test_publicar_exige_sesion_privilegiada(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, published: list[UUID]
) -> None:
    _, token = await staff_login(api_client, committed_login, Role.ADMIN, priv=False)

    response = await publish(api_client, token, published)

    assert response.status_code == 401
    assert problem_type(response) == "reauthentication-required"


async def test_publicar_una_version_exige_a_todos_volver_a_autorizar(
    api_client: httpx.AsyncClient,
    committed_login: CommittedLogin,
    published: list[UUID],
    app_engine: AsyncEngine,
) -> None:
    admin, admin_token = await staff_login(api_client, committed_login, Role.ADMIN, priv=True)
    _, student_token = await committed_login()
    await decide(api_client, student_token, "accepted")
    assert await consent_required(api_client, student_token) is False

    response = await publish(api_client, admin_token, published, version="9000.1")

    assert response.status_code == 201, response.text
    version = response.json()
    assert set(version) == {"id", "version", "title", "body_markdown", "effective_from"}
    assert version["version"] == "9000.1"
    assert (await current_policy(api_client))["id"] == version["id"]
    me = (await api_client.get("/api/v1/me", headers=bearer(student_token))).json()
    assert me["onboarding"]["consent_required"] is True
    assert me["onboarding"]["current_policy_version_id"] == version["id"]
    async with app_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    """SELECT actor_id, target_type, details FROM identity.audit_events
                       WHERE action = 'policy.published' AND target_id = :id"""
                ),
                {"id": version["id"]},
            )
        ).one()
        published_by = (
            await conn.execute(
                text("SELECT published_by FROM identity.policy_versions WHERE id = :id"),
                {"id": version["id"]},
            )
        ).scalar_one()
    assert (row.actor_id, row.target_type) == (admin.id, "policy")
    assert row.details == {"version": "9000.1"}
    assert published_by == admin.id


async def test_una_version_repetida_responde_409(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, published: list[UUID]
) -> None:
    _, token = await staff_login(api_client, committed_login, Role.ADMIN, priv=True)

    response = await publish(api_client, token, published, version="1.0")

    assert response.status_code == 409
    assert problem_type(response) == "policy-version-exists"


async def test_una_vigencia_no_posterior_a_la_ultima_version_responde_422(
    api_client: httpx.AsyncClient, committed_login: CommittedLogin, published: list[UUID]
) -> None:
    _, token = await staff_login(api_client, committed_login, Role.ADMIN, priv=True)
    policy = await current_policy(api_client)

    response = await publish(api_client, token, published, effective_from=policy["effective_from"])

    assert response.status_code == 422
    assert problem_type(response) == "effective-from-too-early"


@pytest.mark.parametrize(
    "overrides",
    [{"version": "v2"}, {"body_markdown": "corto"}, {"title": "t" * 201}],
    ids=["version", "texto", "titulo"],
)
async def test_datos_invalidos_responden_422(
    api_client: httpx.AsyncClient,
    committed_login: CommittedLogin,
    published: list[UUID],
    overrides: dict[str, Any],
) -> None:
    _, token = await staff_login(api_client, committed_login, Role.ADMIN, priv=True)

    response = await publish(api_client, token, published, **overrides)

    assert response.status_code == 422
