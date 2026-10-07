"""T073: flujo HTTP de ingreso con Microsoft (FR-001 a FR-005, FR-036; R-10 a R-13, R-31).

La app completa (`create_app`) con PostgreSQL y Redis reales; Entra ID se simula con respx.
"""

import io
import json
import time
from collections.abc import AsyncIterator, Iterator
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from jwt.algorithms import RSAAlgorithm
from redis.asyncio import Redis
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.main import create_app
from tests.integration.conftest import TEST_TENANT, settings_for

OTHER_TENANT = UUID("22222222-2222-4222-8222-222222222222")
CLIENT_ID = "33333333-3333-4333-8333-333333333333"
AUTHORITY = f"https://login.microsoftonline.com/{TEST_TENANT}/v2.0"
BASE = f"https://login.microsoftonline.com/{TEST_TENANT}"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EMAIL = "ana.perez@unilibre.edu.co"


@pytest.fixture
def idp() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{AUTHORITY}/.well-known/openid-configuration").respond(
            json={
                "issuer": AUTHORITY,
                "authorization_endpoint": f"{BASE}/oauth2/v2.0/authorize",
                "token_endpoint": f"{BASE}/oauth2/v2.0/token",
                "jwks_uri": f"{BASE}/discovery/v2.0/keys",
            }
        )
        public: dict[str, Any] = RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
        router.get(f"{BASE}/discovery/v2.0/keys").respond(
            json={"keys": [{**public, "kid": "k1", "alg": "RS256"}]}
        )
        yield router


class Flow:
    def __init__(self, app: FastAPI, logs: io.StringIO, idp: respx.MockRouter) -> None:
        self.app, self.logs, self.idp = app, logs, idp

    def client(self) -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=self.app, client=("198.51.100.20", 40000))
        return httpx.AsyncClient(transport=transport, base_url="http://localhost")

    async def start(self, return_to: str | None = None) -> tuple[httpx.Response, dict[str, str]]:
        params = {"return_to": return_to} if return_to else {}
        async with self.client() as http:
            response = await http.get("/api/auth/microsoft/login", params=params)
        location = parse_qs(urlsplit(response.headers.get("location", "")).query)
        return response, {k: v[0] for k, v in location.items()}

    def id_token(self, nonce: str, oid: UUID, tid: UUID = TEST_TENANT, **extra: Any) -> str:
        now = int(time.time())
        claims = {
            "iss": AUTHORITY,
            "aud": CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            "nonce": nonce,
            "tid": str(tid),
            "oid": str(oid),
            "name": "Ana Pérez",
            "email": EMAIL,
            **extra,
        }
        return jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "k1"})

    async def callback(self, start: httpx.Response, *, state: str, **query: str) -> httpx.Response:
        cookie = SimpleCookie()
        cookie.load(start.headers["set-cookie"])
        async with self.client() as http:
            return await http.get(
                "/api/auth/microsoft/callback",
                params={"state": state, **query},
                headers={"Cookie": f"su_oidc={cookie['su_oidc'].value}"},
            )

    async def login(
        self, oid: UUID, *, return_to: str | None = None, **claims: Any
    ) -> httpx.Response:
        start, params = await self.start(return_to)
        self.idp.post(f"{BASE}/oauth2/v2.0/token").respond(
            json={"token_type": "Bearer", "id_token": self.id_token(params["nonce"], oid, **claims)}
        )
        return await self.callback(start, state=params["state"], code="codigo")

    def log_lines(self) -> list[dict[str, Any]]:
        return [json.loads(line) for line in self.logs.getvalue().splitlines() if line.strip()]


@pytest.fixture
async def created_oids(migrated_database: dict[str, str]) -> AsyncIterator[list[UUID]]:
    oids: list[UUID] = []
    yield oids
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        ids = list(
            (
                await conn.execute(
                    text("SELECT id FROM identity.users WHERE entra_object_id = ANY(:o)"),
                    {"o": oids},
                )
            ).scalars()
        )
        for statement in (
            "DELETE FROM identity.consents WHERE user_id = ANY(:ids)",
            "DELETE FROM identity.audit_events WHERE subject_user_id = ANY(:ids)",
            "DELETE FROM identity.users WHERE id = ANY(:ids)",
        ):
            await conn.execute(text(statement), {"ids": ids})
    await engine.dispose()


@pytest.fixture
def flow(
    migrated_database: dict[str, str], redis_url: str, redis_client: Redis, idp: respx.MockRouter
) -> Flow:
    logs = io.StringIO()
    app = create_app(settings_for(migrated_database, redis_url), log_stream=logs)
    return Flow(app, logs, idp)


def new_oid(created: list[UUID]) -> UUID:
    oid = uuid4()
    created.append(oid)
    return oid


def location(response: httpx.Response) -> str:
    assert response.status_code == 302, response.text
    return response.headers["location"]


async def count_users(engine: AsyncEngine, oid: UUID) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT count(*) FROM identity.users WHERE entra_object_id = :o"), {"o": oid}
        )
        return int(result.scalar_one())


# --- Inicio ------------------------------------------------------------------------------------


async def test_login_redirige_a_la_autoridad_del_inquilino_con_cookie_firmada(flow: Flow) -> None:
    response, params = await flow.start("/mi-cuenta")

    assert location(response).startswith(f"{BASE}/oauth2/v2.0/authorize?")
    assert params["code_challenge_method"] == "S256"
    assert "common" not in location(response)
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    oidc = cookie["su_oidc"]
    assert oidc["httponly"] is True
    assert oidc["path"] == "/api/auth/microsoft"
    assert oidc["samesite"].lower() == "lax"
    assert int(oidc["max-age"]) == 600
    # El estado viaja firmado: el valor en claro no aparece en la cookie.
    assert params["state"] not in oidc.value


async def test_proveedor_caido_al_iniciar(flow: Flow, idp: respx.MockRouter) -> None:
    idp.get(f"{AUTHORITY}/.well-known/openid-configuration").respond(503)

    response, _ = await flow.start()

    assert location(response) == "/ingresar?error=idp_unavailable"


async def test_limite_de_30_por_minuto_por_ip(flow: Flow) -> None:
    statuses = [(await flow.start())[0].status_code for _ in range(31)]

    assert statuses[:30] == [302] * 30
    assert statuses[30] == 429


# --- Retorno -----------------------------------------------------------------------------------


async def test_primer_ingreso_valido_crea_la_cuenta_y_lleva_a_la_autorizacion(
    flow: Flow, created_oids: list[UUID], app_engine: AsyncEngine
) -> None:
    oid = new_oid(created_oids)

    response = await flow.login(oid)

    assert location(response) == "/bienvenida/datos"
    cookies = SimpleCookie()
    for value in response.headers.get_list("set-cookie"):
        cookies.load(value)
    refresh = cookies["su_refresh"]
    assert refresh.value
    assert refresh["httponly"] is True
    assert refresh["secure"] is True
    assert refresh["samesite"] == "Strict"
    assert refresh["path"] == "/api/auth"
    assert cookies["su_oidc"]["max-age"] in ("0", "-1") or cookies["su_oidc"].value in ("", "null")
    assert await count_users(app_engine, oid) == 1


async def test_return_to_solo_rutas_internas_y_tras_completar_el_primer_ingreso(
    flow: Flow,
    created_oids: list[UUID],
    app_engine: AsyncEngine,
    migrated_database: dict[str, str],
) -> None:
    oid = new_oid(created_oids)
    await flow.login(oid)
    # Completa el primer ingreso: autorización vigente y perfil.
    async with app_engine.begin() as conn:
        user_id = (
            await conn.execute(
                text("SELECT id FROM identity.users WHERE entra_object_id = :o"), {"o": oid}
            )
        ).scalar_one()
        version = (
            await conn.execute(
                text(
                    """INSERT INTO identity.policy_versions (version, title, body_markdown,
                           effective_from) VALUES (:v, 'Política', '...', now() - interval '1 day')
                       RETURNING id"""
                ),
                {"v": f"t-{uuid4()}"},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
                   VALUES (:u, :p, 'accepted', 'web_pwa')"""
            ),
            {"u": user_id, "p": version},
        )
        await conn.execute(
            text("UPDATE identity.users SET onboarding_completed_at = now() WHERE id = :u"),
            {"u": user_id},
        )
    try:
        assert location(await flow.login(oid, return_to="/mi-cuenta")) == "/mi-cuenta"
        assert location(await flow.login(oid, return_to="//otro.example.com")) == "/inicio"
        assert location(await flow.login(oid, return_to="https://otro.example.com")) == "/inicio"
    finally:
        # saber_app no puede borrar versiones de la política: limpia saber_migrator.
        migrator = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
        async with migrator.begin() as conn:
            await conn.execute(
                text("DELETE FROM identity.consents WHERE policy_version_id = :p"), {"p": version}
            )
            await conn.execute(
                text("DELETE FROM identity.policy_versions WHERE id = :p"), {"p": version}
            )
        await migrator.dispose()


async def test_inquilino_externo_se_rechaza_sin_crear_cuenta_y_sin_correo_en_logs(
    flow: Flow, created_oids: list[UUID], app_engine: AsyncEngine
) -> None:
    oid = new_oid(created_oids)

    response = await flow.login(oid, tid=OTHER_TENANT)

    assert location(response) == "/ingresar?error=tenant_not_allowed"
    assert "su_refresh" not in response.headers.get("set-cookie", "")
    assert await count_users(app_engine, oid) == 0
    rejected = [line for line in flow.log_lines() if line["event"] == "auth.login_rejected"]
    assert [line["cause"] for line in rejected] == ["tenant_not_allowed"]
    assert EMAIL not in flow.logs.getvalue()


async def test_state_distinto_se_rechaza(flow: Flow, created_oids: list[UUID]) -> None:
    start, _ = await flow.start()

    response = await flow.callback(start, state="otro-estado", code="codigo")

    assert location(response) == "/ingresar?error=invalid_state"


async def test_sin_cookie_de_estado_se_rechaza(flow: Flow) -> None:
    async with flow.client() as http:
        response = await http.get(
            "/api/auth/microsoft/callback", params={"state": "x", "code": "y"}
        )

    assert location(response) == "/ingresar?error=invalid_state"


async def test_el_usuario_cancela_en_microsoft(flow: Flow) -> None:
    start, params = await flow.start()

    response = await flow.callback(start, state=params["state"], error="access_denied")

    assert location(response) == "/ingresar?error=login_cancelled"


async def test_proveedor_caido_en_el_canje(flow: Flow, idp: respx.MockRouter) -> None:
    start, params = await flow.start()
    idp.post(f"{BASE}/oauth2/v2.0/token").respond(500)

    response = await flow.callback(start, state=params["state"], code="codigo")

    assert location(response) == "/ingresar?error=idp_unavailable"


async def test_id_token_invalido(flow: Flow, idp: respx.MockRouter) -> None:
    start, params = await flow.start()
    idp.post(f"{BASE}/oauth2/v2.0/token").respond(
        json={"token_type": "Bearer", "id_token": flow.id_token("otro-nonce", uuid4())}
    )

    response = await flow.callback(start, state=params["state"], code="codigo")

    assert location(response) == "/ingresar?error=login_failed"


async def test_cuenta_desactivada(
    flow: Flow, created_oids: list[UUID], app_engine: AsyncEngine
) -> None:
    oid = new_oid(created_oids)
    await flow.login(oid)
    async with app_engine.begin() as conn:
        await conn.execute(
            text("UPDATE identity.users SET status = 'disabled' WHERE entra_object_id = :o"),
            {"o": oid},
        )

    assert location(await flow.login(oid)) == "/ingresar?error=account_disabled"
