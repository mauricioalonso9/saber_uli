"""T182: cuenta local de administración (US9; FR-040 a FR-047, SC-009; R-41, ADR 0009).

La migración crea `adminsaber` con la contraseña inicial `adminsaber` y el cambio obligatorio.
Cada prueba la deja como la encontró (contraseña inicial, sin bloqueo).
"""

import asyncio
import logging
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.domain.local_credential import INITIAL_PASSWORD
from saber_uli.identity.infrastructure.passwords import Argon2PasswordHasher

SESSIONS = "/api/auth/local/sessions"
PASSWORD = "/api/auth/local/password"
ME = "/api/v1/me"
NEW_PASSWORD = "una frase larga de prueba 2026"


async def reset_local_admin(migrator_url: str) -> None:
    engine = create_async_engine(migrator_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """UPDATE identity.local_credentials SET password_hash = :hash,
                       must_change = true, failed_attempts = 0, locked_until = NULL
                   WHERE user_id = (SELECT id FROM identity.users WHERE username = 'adminsaber')"""
            ),
            {"hash": Argon2PasswordHasher().hash("adminsaber")},
        )
        await conn.execute(
            text("UPDATE identity.users SET status = 'active' WHERE username = 'adminsaber'")
        )
    await engine.dispose()


@pytest.fixture(autouse=True)
async def local_admin(migrated_database: dict[str, str]) -> AsyncIterator[None]:
    await reset_local_admin(migrated_database["migrator"])
    yield
    await reset_local_admin(migrated_database["migrator"])


async def sign_in(client: httpx.AsyncClient, password: str = INITIAL_PASSWORD) -> httpx.Response:
    return await client.post(SESSIONS, json={"username": "adminsaber", "password": password})


def bearer(response: httpx.Response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def audit_actions(engine: AsyncEngine) -> list[tuple[str, dict[str, Any]]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                """SELECT action, details FROM identity.audit_events
                   WHERE subject_user_id = (SELECT id FROM identity.users
                                            WHERE username = 'adminsaber')
                   ORDER BY occurred_at, id"""
            )
        )
        return [(r.action, dict(r.details)) for r in rows]


async def test_la_migracion_crea_la_cuenta_local(app_engine: AsyncEngine) -> None:
    async with app_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    """SELECT u.kind, u.status, u.email, u.display_name,
                              u.onboarding_completed_at IS NOT NULL AS onboarded,
                              c.must_change, c.password_hash,
                              array(SELECT r.role FROM identity.role_assignments r
                                    WHERE r.user_id = u.id) AS roles
                       FROM identity.users u
                       JOIN identity.local_credentials c ON c.user_id = u.id
                       WHERE u.username = 'adminsaber'"""
                )
            )
        ).one()

    assert (row.kind, row.status, row.email) == ("local", "active", None)
    assert row.display_name == "Administración Saber Uli"
    assert row.onboarded is True
    assert row.must_change is True
    assert row.password_hash.startswith("$argon2id$")
    assert "admin" in row.roles


async def test_la_contrasena_inicial_solo_permite_cambiarla(api_client: httpx.AsyncClient) -> None:
    signed = await sign_in(api_client)

    assert signed.status_code == 200, signed.text
    assert "su_refresh=" in signed.headers["set-cookie"]
    me = await api_client.get(ME, headers=bearer(signed))
    assert me.status_code == 200
    body = me.json()
    assert body["kind"] == "local"
    assert body["email"] is None
    onboarding = body["onboarding"]
    assert (
        onboarding["consent_required"],
        onboarding["profile_required"],
        onboarding["password_change_required"],
    ) == (False, False, True)
    assert body["permissions"] == []
    blocked = [
        await api_client.get(path, headers=bearer(signed))
        for path in ("/api/v1/admin/users", "/api/v1/me/sessions", "/api/v1/content/items")
    ]
    assert [r.status_code for r in blocked] == [403, 403, 403]
    assert all(r.json()["type"].endswith("password-change-required") for r in blocked)


async def test_credenciales_incorrectas_dan_el_mismo_401(api_client: httpx.AsyncClient) -> None:
    wrong = await sign_in(api_client, "otra contraseña")
    unknown = await api_client.post(SESSIONS, json={"username": "nadie", "password": "x"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["type"] == unknown.json()["type"]
    assert wrong.json()["type"].endswith("invalid-credentials")
    assert wrong.json()["detail"] == unknown.json()["detail"]


async def test_diez_fallos_bloquean_la_cuenta(
    api_client: httpx.AsyncClient, app_engine: AsyncEngine
) -> None:
    failures = [(await sign_in(api_client, f"mala {n}")).status_code for n in range(10)]
    locked = await sign_in(api_client)

    assert failures == [401] * 10
    assert locked.status_code == 429
    assert locked.json()["type"].endswith("account-locked")
    assert 0 < int(locked.headers["Retry-After"]) <= 15 * 60
    actions = [action for action, _ in await audit_actions(app_engine)]
    assert actions.count("auth.login_rejected") >= 10
    assert "auth.local_locked" in actions


async def test_cambiar_la_contrasena(
    api_client: httpx.AsyncClient, app_engine: AsyncEngine, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    first = await sign_in(api_client)
    other = await sign_in(api_client)
    headers = bearer(first)

    def change(current: str, new: str) -> Any:
        return api_client.post(
            PASSWORD, json={"current_password": current, "new_password": new}, headers=headers
        )

    short = await change("adminsaber", "corta")
    same_user = await change("adminsaber", "AdminSaber  ")
    common = await change("adminsaber", "password1234")
    wrong_current = await change("no es", NEW_PASSWORD)
    changed = await change("adminsaber", NEW_PASSWORD)

    assert [r.status_code for r in (short, same_user, common)] == [422, 422, 422]
    assert all(r.json()["type"].endswith("weak-password") for r in (short, same_user, common))
    assert "12" in short.json()["detail"]
    assert wrong_current.status_code == 403
    assert changed.status_code == 200, changed.text
    assert "su_refresh=" in changed.headers["set-cookie"]
    me = (await api_client.get(ME, headers=bearer(changed))).json()
    assert me["onboarding"]["password_change_required"] is False
    assert "users:manage" in me["permissions"]
    # Las sesiones anteriores quedaron cerradas (FR-045).
    stale = await api_client.get(ME, headers=bearer(other))
    assert stale.status_code == 401
    again = await sign_in(api_client, NEW_PASSWORD)
    assert again.status_code == 200
    assert (await sign_in(api_client, "adminsaber")).status_code == 401
    actions = [action for action, _ in await audit_actions(app_engine)]
    assert "auth.password_changed" in actions
    assert "auth.local_login_succeeded" in actions
    for secret in ('adminsaber"', NEW_PASSWORD, "password1234"):
        assert secret not in caplog.text


async def test_el_comando_restablece_la_contrasena_inicial(
    api_client: httpx.AsyncClient, migrated_database: dict[str, str], app_engine: AsyncEngine
) -> None:
    signed = await sign_in(api_client)
    await api_client.post(
        PASSWORD,
        json={"current_password": "adminsaber", "new_password": NEW_PASSWORD},
        headers=bearer(signed),
    )
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["DATABASE_URL"] = migrated_database["app"]

    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "saber_uli.cli", "identity", "reset-local-password"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "adminsaber" in result.stdout
    assert NEW_PASSWORD not in result.stdout + result.stderr
    restored = await sign_in(api_client)
    assert restored.status_code == 200
    me = (await api_client.get(ME, headers=bearer(restored))).json()
    assert me["onboarding"]["password_change_required"] is True
    actions = [action for action, _ in await audit_actions(app_engine)]
    assert "auth.password_reset" in actions


async def test_la_cuenta_local_no_entra_en_la_retencion(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> None:
    from datetime import UTC, datetime, timedelta

    from saber_uli.identity.application.retention import schedule_for
    from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
    from saber_uli.shared.application.event_bus import EventBus
    from saber_uli.shared.infrastructure.db import create_session_factory

    factory = create_session_factory(app_engine)
    async with app_engine.connect() as conn:
        user_id: UUID = (
            await conn.execute(text("SELECT id FROM identity.users WHERE username = 'adminsaber'"))
        ).scalar_one()
    async with SqlAlchemyIdentityUnitOfWork(factory, EventBus()) as uow:
        user = await uow.users.get(user_id)
        assert user is not None
        schedule = await schedule_for(uow, user, now=datetime.now(UTC) + timedelta(days=3 * 365))

    assert schedule is None
