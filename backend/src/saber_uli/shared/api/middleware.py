"""Middlewares ASGI de la API.

- `RequestLoggingMiddleware`: un log JSON por petición (`http_request`) con método, ruta sin la
  consulta, estado, duración e identificador de petición (también en `X-Request-ID`). La ruta
  nunca incluye la cadena de consulta: podría llevar datos personales (R-23).
- `PathScopedMiddleware`: aplica otro middleware solo bajo un prefijo de ruta (por ejemplo, la
  sesión firmada del flujo OIDC solo en `/api/auth/microsoft`).
"""

import time
import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_log = structlog.get_logger("saber_uli.http")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                _log.info(
                    "http_request",
                    method=scope["method"],
                    path=scope["path"],
                    status=status,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )


class PathScopedMiddleware:
    def __init__(
        self, app: ASGIApp, *, prefix: str, middleware: type, options: dict[str, Any]
    ) -> None:
        self.app = app
        self.prefix = prefix
        self.scoped = middleware(app, **options)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and str(scope["path"]).startswith(self.prefix):
            await self.scoped(scope, receive, send)
        else:
            await self.app(scope, receive, send)
