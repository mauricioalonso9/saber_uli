"""T057: arranque de la API, salud, disponibilidad y logs por petición (research R-23, R-32)."""

import io
import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from redis.asyncio import Redis

from saber_uli.main import create_app
from tests.integration.conftest import settings_for


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def log_lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


@pytest.fixture
def app(migrated_database: dict[str, str], redis_url: str, redis_client: Redis) -> FastAPI:
    return create_app(settings_for(migrated_database, redis_url), log_stream=io.StringIO())


async def test_health(app: FastAPI) -> None:
    async with client(app) as http:
        response = await http.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_con_base_de_datos_y_redis(app: FastAPI) -> None:
    async with client(app) as http:
        response = await http.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


@pytest.mark.parametrize("broken", ["database", "redis"])
async def test_ready_responde_503_si_falta_una_dependencia(
    migrated_database: dict[str, str], redis_url: str, broken: str
) -> None:
    urls = dict(migrated_database)
    if broken == "database":
        urls["app"] = urls["app"].rsplit("@", 1)[0] + "@127.0.0.1:1/saber_uli"
    redis = "redis://127.0.0.1:1/0" if broken == "redis" else redis_url
    app = create_app(settings_for(urls, redis), log_stream=io.StringIO())

    async with client(app) as http:
        response = await http.get("/api/ready")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "urn:saber-uli:problem:service-unavailable"


async def test_cada_peticion_deja_un_log_json_sin_datos_personales(
    migrated_database: dict[str, str], redis_url: str, redis_client: Redis
) -> None:
    stream = io.StringIO()
    app = create_app(settings_for(migrated_database, redis_url), log_stream=stream)

    async with client(app) as http:
        await http.get("/api/health?correo=ana@unilibre.edu.co")
        await http.get("/no-existe")

    requests = [line for line in log_lines(stream) if line["event"] == "http_request"]
    assert [(r["method"], r["path"], r["status"]) for r in requests] == [
        ("GET", "/api/health", 200),
        ("GET", "/no-existe", 404),
    ]
    assert all(isinstance(r["duration_ms"], float) for r in requests)
    assert all(r["request_id"] for r in requests)
    assert "ana@unilibre.edu.co" not in stream.getvalue()


async def test_errores_como_problem_details_y_rutas_de_sesion(app: FastAPI) -> None:
    async with client(app) as http:
        missing = await http.get("/api/v1/no-existe")
        refresh = await http.post("/api/auth/refresh")

    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")
    assert refresh.status_code == 401
    assert refresh.json()["type"] == "urn:saber-uli:problem:unauthenticated"


async def test_la_cookie_de_sesion_oidc_no_sale_fuera_de_su_ruta(app: FastAPI) -> None:
    async with client(app) as http:
        response = await http.get("/api/health")

    assert "set-cookie" not in response.headers


async def test_cliente_asgi_de_las_pruebas(api_client: httpx.AsyncClient) -> None:
    assert (await api_client.get("/api/health")).json() == {"status": "ok"}
