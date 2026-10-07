"""T035: limitación de peticiones (research R-31; principio IX) con Redis real.

Ventanas: 5/h por correo y 20/h por IP al pedir enlace de invitado; 10/min por IP al consumirlo;
120/min por IP al iniciar el ingreso con Microsoft; 30/min por sesión y 600/min por IP en la
renovación (precisión de R-31 en T081: el campus sale por una sola IP); 300/min por usuario en
el resto.
Respuesta 429 `rate-limited` con `Retry-After`. La clave por correo es un HMAC: el correo nunca
llega a Redis.
"""

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI, Header, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from structlog.testing import capture_logs

from saber_uli.shared.api.problems import PROBLEM_MEDIA_TYPE, install_problem_handlers
from saber_uli.shared.api.rate_limit import (
    RateLimitGuard,
    per_ip,
    per_user,
    rate_limit_guard,
)
from saber_uli.shared.infrastructure.rate_limit import (
    API_PER_USER,
    GUEST_LINK_PER_EMAIL,
    GUEST_LINK_PER_IP,
    GUEST_SESSION_PER_IP,
    MICROSOFT_LOGIN_PER_IP,
    REFRESH_PER_IP,
    REFRESH_PER_SESSION,
    RateLimiter,
)

HASH_KEY = b"clave-de-prueba-para-hmac-de-correos-32b"


class LinkRequest(BaseModel):
    email: str


def user_from_header(x_test_user: Annotated[str, Header()]) -> str:
    """Sustituto de `current_user` (T048) para la prueba."""
    return x_test_user


def build_app(limiter: RateLimiter) -> FastAPI:
    app = FastAPI()
    install_problem_handlers(app)
    app.state.rate_limiter = limiter

    @app.post("/api/auth/guest/link-requests", dependencies=[Depends(per_ip(GUEST_LINK_PER_IP))])
    async def link_requests(
        body: LinkRequest, guard: Annotated[RateLimitGuard, Depends(rate_limit_guard)]
    ) -> dict[str, str]:
        await guard.check_email(GUEST_LINK_PER_EMAIL, body.email)
        return {"status": "accepted"}

    @app.post("/api/auth/guest/sessions", dependencies=[Depends(per_ip(GUEST_SESSION_PER_IP))])
    async def guest_sessions() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/auth/microsoft/login", dependencies=[Depends(per_ip(MICROSOFT_LOGIN_PER_IP))])
    async def microsoft_login() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/refresh", dependencies=[Depends(per_ip(REFRESH_PER_IP))])
    async def refresh(
        guard: Annotated[RateLimitGuard, Depends(rate_limit_guard)],
        x_session: Annotated[str, Header()] = "sin-sesion",
    ) -> dict[str, str]:
        await guard.check_opaque(REFRESH_PER_SESSION, x_session)
        return {"status": "ok"}

    @app.get("/api/v1/algo", dependencies=[Depends(per_user(API_PER_USER, user_from_header))])
    async def algo(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.fixture
async def limiter(redis_url: str, redis_client: Redis) -> AsyncIterator[RateLimiter]:
    yield RateLimiter(redis_url, hash_key=HASH_KEY)


def client(app: FastAPI, ip: str = "203.0.113.10") -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(ip, 51000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def hit(
    http: httpx.AsyncClient,
    times: int,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
) -> list[int]:
    return [(await http.request(method, url, headers=headers)).status_code for _ in range(times)]


def assert_rate_limited(response: httpx.Response, window_seconds: int) -> None:
    assert response.status_code == 429
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    assert response.json()["type"] == "urn:saber-uli:problem:rate-limited"
    retry_after = int(response.headers["Retry-After"])
    assert 1 <= retry_after <= window_seconds


# --- Solicitud de enlace de invitado -----------------------------------------------------------


async def test_cinco_por_hora_por_correo_aunque_cambie_la_ip(limiter: RateLimiter) -> None:
    app = build_app(limiter)
    statuses = []
    for n in range(5):
        async with client(app, f"198.51.100.{n}") as http:
            statuses.append(
                (
                    await http.post(
                        "/api/auth/guest/link-requests", json={"email": "ana@correo.co"}
                    )
                ).status_code
            )
    assert statuses == [200] * 5

    async with client(app, "198.51.100.99") as http:
        # Misma persona con mayúsculas y espacios: mismo cupo.
        blocked = await http.post(
            "/api/auth/guest/link-requests", json={"email": "  ANA@Correo.co "}
        )
        other = await http.post("/api/auth/guest/link-requests", json={"email": "otra@correo.co"})

    assert_rate_limited(blocked, 3600)
    assert other.status_code == 200


async def test_veinte_por_hora_por_ip(limiter: RateLimiter) -> None:
    async with client(build_app(limiter)) as http:
        statuses = [
            (
                await http.post(
                    "/api/auth/guest/link-requests", json={"email": f"persona{n}@correo.co"}
                )
            ).status_code
            for n in range(21)
        ]

    assert statuses == [200] * 20 + [429]


async def test_la_clave_por_correo_es_un_hmac(limiter: RateLimiter, redis_client: Redis) -> None:
    async with client(build_app(limiter)) as http:
        await http.post("/api/auth/guest/link-requests", json={"email": "secreta@correo.co"})

    keys = [key.decode() async for key in redis_client.scan_iter("*")]
    assert keys
    assert not [key for key in keys if "secreta" in key or "correo.co" in key]


# --- Consumo de enlace, Microsoft y renovación -------------------------------------------------


async def test_diez_por_minuto_por_ip_al_consumir_el_enlace(limiter: RateLimiter) -> None:
    app = build_app(limiter)
    async with client(app) as http:
        statuses = await hit(http, 11, "POST", "/api/auth/guest/sessions")
        last = await http.post("/api/auth/guest/sessions")
    async with client(app, "192.0.2.50") as other_ip:
        other = await other_ip.post("/api/auth/guest/sessions")

    assert statuses == [200] * 10 + [429]
    assert_rate_limited(last, 60)
    assert other.status_code == 200


async def test_ingreso_con_microsoft_120_por_minuto_por_ip(limiter: RateLimiter) -> None:
    # Un salón completo detrás de la misma IP del campus puede ingresar a la vez.
    async with client(build_app(limiter)) as http:
        statuses = await hit(http, 120, "GET", "/api/auth/microsoft/login")
        blocked = await http.get("/api/auth/microsoft/login")

    assert statuses == [200] * 120
    assert_rate_limited(blocked, 60)


async def test_renovacion_30_por_minuto_por_sesion(
    limiter: RateLimiter, redis_client: Redis
) -> None:
    async with client(build_app(limiter)) as http:
        mine = await hit(http, 30, "POST", "/api/auth/refresh", headers={"X-Session": "cookie-a"})
        blocked = await http.post("/api/auth/refresh", headers={"X-Session": "cookie-a"})
        other = await http.post("/api/auth/refresh", headers={"X-Session": "cookie-b"})

    assert mine == [200] * 30
    assert_rate_limited(blocked, 60)
    # Otra sesión detrás de la misma IP no se ve afectada.
    assert other.status_code == 200
    # La cookie nunca llega a Redis: la clave es un HMAC.
    keys = [key.decode() async for key in redis_client.scan_iter("*")]
    assert not [key for key in keys if "cookie-a" in key]


async def test_renovacion_600_por_minuto_por_ip(limiter: RateLimiter) -> None:
    async with client(build_app(limiter)) as http:
        statuses = [
            (await http.post("/api/auth/refresh", headers={"X-Session": f"s{n}"})).status_code
            for n in range(601)
        ]

    assert statuses == [200] * 600 + [429]


# --- Resto de la API ---------------------------------------------------------------------------


async def test_trescientos_por_minuto_por_usuario(limiter: RateLimiter) -> None:
    async with client(build_app(limiter)) as http:
        statuses = await hit(http, 300, "GET", "/api/v1/algo", headers={"X-Test-User": "u1"})
        blocked = await http.get("/api/v1/algo", headers={"X-Test-User": "u1"})
        other = await http.get("/api/v1/algo", headers={"X-Test-User": "u2"})

    assert statuses == [200] * 300
    assert_rate_limited(blocked, 60)
    assert other.status_code == 200


# --- Redis caído -------------------------------------------------------------------------------


async def test_si_redis_no_responde_se_permite_y_se_registra() -> None:
    # Puerto sin servidor: la limitación no debe tumbar la API (R-16 tolera la caída de Redis).
    unavailable = RateLimiter("redis://127.0.0.1:1/0", hash_key=HASH_KEY)
    with capture_logs() as logs:
        async with client(build_app(unavailable)) as http:
            response = await http.post("/api/auth/guest/sessions")

    assert response.status_code == 200
    assert any(entry["event"] == "rate_limit_unavailable" for entry in logs)
    assert "203.0.113.10" not in repr(logs)
