"""T176: presupuestos de rendimiento sobre 40 000 usuarios sembrados (plan, metas de rendimiento).

- p95 < 300 ms en `GET /api/v1/me`, `POST /api/auth/refresh` y `GET /api/v1/invitations` con 200
  peticiones concurrentes.
- Validación de un lote de 500 filas (`POST /api/v1/invitation-batches`) en menos de 2 s.

La app ASGI completa corre en el mismo proceso que el cliente (un solo proceso, frente a los 4
de producción), con PostgreSQL y Redis reales. Se mide la latencia sin carga (peticiones en
serie) y con las 200 a la vez. El lote siempre debe cumplir su presupuesto; los p95 solo se exigen
con `PERF_BUDGETS_ENFORCE=1`, en hardware de referencia: en Windows con Docker Desktop cada viaje
a PostgreSQL y Redis pasa por la VM y las 200 peticiones simultáneas hacen cola en un solo
proceso (mediciones y decisión pendiente en tasks.md, T176). El reporte se imprime siempre.

Los datos sembrados se borran al terminar con `saber_migrator`.
"""

import asyncio
import io
import math
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID, uuid4

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.api.auth_router import REFRESH_COOKIE
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import AuthMethod
from tests.integration.conftest import TEST_TENANT, CommittedLogin, settings_for
from tests.integration.identity.staff import StaffFactory

SEEDED_USERS = 40_000
SEEDED_GUESTS = 10_000  # de los 40 000, con su invitación aceptada
CONCURRENCY = 200
SERIAL = 20
P95_BUDGET_MS = 300
BATCH_ROWS = 500
BATCH_BUDGET_S = 2.0
LISTING_ADMINS = 10  # 20 peticiones cada uno: lejos del límite de 300 por minuto por usuario
XRW = {"X-Requested-With": "saber-uli"}
SEED_MARK = "carga-t176-"


@pytest.fixture
async def seeded(migrated_database: dict[str, str]) -> AsyncIterator[None]:
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    institutional = SEEDED_USERS - SEEDED_GUESTS
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO identity.users
                       (kind, entra_tenant_id, entra_object_id, email, display_name, last_login_at)
                   SELECT 'institutional', :tenant, gen_random_uuid(),
                          :mark || g || '@unilibre.edu.co', 'Persona de carga ' || g,
                          now() - (g % 180) * interval '1 day'
                   FROM generate_series(1, :n) AS g"""
            ),
            {"tenant": TEST_TENANT, "mark": SEED_MARK, "n": institutional},
        )
        await conn.execute(
            text(
                """INSERT INTO identity.users (kind, email, display_name, last_login_at)
                   SELECT 'guest', :mark || 'inv-' || g || '@correo.co', 'Invitado ' || g,
                          now() - (g % 30) * interval '1 day'
                   FROM generate_series(1, :n) AS g"""
            ),
            {"mark": SEED_MARK, "n": SEEDED_GUESTS},
        )
        # Las invitaciones las hizo una de las personas sembradas (como docente).
        await conn.execute(
            text(
                """INSERT INTO identity.invitations
                       (email, invitee_name, invited_by, guest_user_id, status,
                        access_expires_at, sent_at, accepted_at, last_delivery_status)
                   SELECT g.email, g.display_name,
                          (SELECT id FROM identity.users
                           WHERE email = :mark || '1@unilibre.edu.co'),
                          g.id, 'accepted', now() + interval '30 days', now(), now(), 'sent'
                   FROM identity.users AS g
                   WHERE g.kind = 'guest' AND g.email LIKE :mark || 'inv-%'"""
            ),
            {"mark": SEED_MARK},
        )
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("ANALYZE identity.users"))
        await conn.execute(text("ANALYZE identity.invitations"))
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM identity.invitations WHERE email LIKE :mark || '%'"),
            {"mark": SEED_MARK},
        )
        await conn.execute(
            text("DELETE FROM identity.users WHERE email LIKE :mark || '%'"), {"mark": SEED_MARK}
        )
    await engine.dispose()


async def accept_policy(engine: AsyncEngine, user_ids: list[UUID]) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
                   SELECT u, (SELECT id FROM identity.policy_versions
                              WHERE effective_from <= now()
                              ORDER BY effective_from DESC, created_at DESC LIMIT 1),
                          'accepted', 'web_pwa'
                   FROM unnest(CAST(:ids AS uuid[])) AS u"""
            ),
            {"ids": user_ids},
        )


Send = Callable[[], Awaitable[httpx.Response]]


def p95_ms(durations: list[float]) -> float:
    ordered = sorted(durations)
    return ordered[math.ceil(0.95 * len(ordered)) - 1] * 1000


async def timed(send: Send) -> float:
    start = time.perf_counter()
    response = await send()
    elapsed = time.perf_counter() - start
    assert response.status_code == 200, response.text
    return elapsed


async def serial(requests: list[Send]) -> float:
    """Una petición tras otra: p95 en milisegundos sin carga."""
    return p95_ms([await timed(send) for send in requests])


async def burst(requests: list[Send]) -> float:
    """Todas las peticiones a la vez: p95 en milisegundos."""
    return p95_ms(list(await asyncio.gather(*(timed(send) for send in requests))))


async def test_presupuestos_de_rendimiento_con_40_000_usuarios(
    seeded: None,
    migrated_database: dict[str, str],
    redis_url: str,
    redis_client: Redis,
    app_engine: AsyncEngine,
    committed_login: CommittedLogin,
    staff: StaffFactory,
) -> None:
    from saber_uli.main import create_app

    app = create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())
    user_ids: list[UUID] = []
    tokens: list[str] = []
    refresh_tokens: list[str] = []
    for _ in range(CONCURRENCY + SERIAL):
        user, token = await committed_login(Role.STUDENT)
        assert user.id is not None
        user_ids.append(user.id)
        tokens.append(token)
        issued = await app.state.session_service.open_session(user.id, AuthMethod.ENTRA_ID)
        refresh_tokens.append(issued.refresh_token)
    await accept_policy(app_engine, user_ids)
    admins = [await staff(Role.ADMIN) for _ in range(LISTING_ADMINS)]
    teacher = await staff(Role.TEACHER)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        def me(token: str) -> Send:
            return lambda: client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

        def refresh(cookie: str) -> Send:
            return lambda: client.post(
                "/api/auth/refresh", headers={**XRW, "Cookie": f"{REFRESH_COOKIE}={cookie}"}
            )

        def invitations(headers: dict[str, str]) -> Send:
            return lambda: client.get("/api/v1/invitations", headers=headers)

        # Calentamiento: conexiones del pool, caché de auth_epoch y planes de consulta.
        for _ in range(3):
            await me(tokens[0])()
            await invitations(admins[0].headers)()

        listing = [
            invitations(admin.headers)
            for admin in admins
            for _ in range(CONCURRENCY // LISTING_ADMINS)
        ]
        measured = {
            "GET /api/v1/me": (
                await serial([me(token) for token in tokens[:SERIAL]]),
                await burst([me(token) for token in tokens[SERIAL:]]),
            ),
            "POST /api/auth/refresh": (
                await serial([refresh(cookie) for cookie in refresh_tokens[:SERIAL]]),
                await burst([refresh(cookie) for cookie in refresh_tokens[SERIAL:]]),
            ),
            "GET /api/v1/invitations": (
                await serial(listing[:SERIAL]),
                await burst(listing),
            ),
        }

        lines = ["correo,nombre,vence"]
        lines += [f"lote-{uuid4().hex[:12]}@correo.co,Persona {i}," for i in range(BATCH_ROWS)]
        start = time.perf_counter()
        response = await client.post(
            "/api/v1/invitation-batches",
            content=("\n".join(lines) + "\n").encode(),
            headers={**teacher.headers, "Content-Type": "text/csv"},
        )
        batch_seconds = time.perf_counter() - start
        assert response.status_code == 201, response.text
        assert response.json()["valid_count"] == BATCH_ROWS

    report = "; ".join(
        f"{name}: p95 {alone:.0f} ms sin carga, {loaded:.0f} ms con {CONCURRENCY} a la vez"
        for name, (alone, loaded) in measured.items()
    )
    report += f"; lote de {BATCH_ROWS} filas: {batch_seconds:.2f} s"
    print(f"\nT176: {report}")
    assert batch_seconds < BATCH_BUDGET_S, report
    if os.environ.get("PERF_BUDGETS_ENFORCE") == "1":
        assert all(loaded < P95_BUDGET_MS for _, loaded in measured.values()), report
