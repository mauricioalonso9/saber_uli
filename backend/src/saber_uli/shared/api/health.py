"""`GET /api/health` (proceso vivo) y `GET /api/ready` (base de datos y Redis), research R-32.

Las comprobaciones de disponibilidad se registran en `app.state.readiness_checks` (nombre →
función asíncrona que lanza si la dependencia no responde). Cada una tiene 2 segundos.
"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Literal

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from saber_uli.shared.api.problems import ProblemException

ReadinessCheck = Callable[[], Awaitable[object]]
_TIMEOUT_SECONDS = 2

_log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["ops"])


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    checks: dict[str, Literal["ok", "failed"]] | None = None


@router.get("/health", operation_id="getHealth", response_model_exclude_none=True)
async def health() -> HealthStatus:
    return HealthStatus(status="ok")


async def _run(name: str, check: ReadinessCheck) -> Literal["ok", "failed"]:
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            await check()
    except Exception as error:
        _log.warning("readiness_check_failed", check=name, error_type=type(error).__name__)
        return "failed"
    return "ok"


@router.get("/ready", operation_id="getReadiness", response_model_exclude_none=True)
async def ready(request: Request) -> HealthStatus:
    checks: Mapping[str, ReadinessCheck] = request.app.state.readiness_checks
    results = dict(
        zip(checks, await asyncio.gather(*(_run(n, c) for n, c in checks.items())), strict=True)
    )
    if any(result == "failed" for result in results.values()):
        raise ProblemException(
            503, "service-unavailable", detail="Un servicio necesario no responde."
        )
    return HealthStatus(status="ok", checks=results)
