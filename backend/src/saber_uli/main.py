"""Raíz de composición de la API (T058).

`create_app()` arma la aplicación a partir de la configuración: logs JSON, base de datos, Redis,
tokens, limitación de peticiones, autenticación, guardia de consentimiento, manejadores de
Problem Details y routers. Se arranca con la fábrica de uvicorn:

    uvicorn --factory saber_uli.main:create_app

así ninguna configuración se lee al importar el módulo (las pruebas pasan la suya).
"""

import hashlib
import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TextIO

from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from saber_uli.config import Settings, get_settings
from saber_uli.identity.api.auth_router import router as auth_router
from saber_uli.identity.api.consent_router import router as consent_router
from saber_uli.identity.api.me_router import router as me_router
from saber_uli.identity.api.microsoft_router import router as microsoft_router
from saber_uli.identity.api.policy_router import router as policy_router
from saber_uli.identity.application.access_guard import AccessGuard
from saber_uli.identity.application.authenticate_institutional_user import (
    AuthenticateInstitutionalUser,
)
from saber_uli.identity.application.consent import ConsentService, PrivacyPolicyService
from saber_uli.identity.application.queries.consent_status import ConsentStatusQuery
from saber_uli.identity.application.queries.get_me import GetMe
from saber_uli.identity.application.sessions import SessionService
from saber_uli.identity.domain.events import UserAccessChanged
from saber_uli.identity.infrastructure.entra_id import EntraIdClient
from saber_uli.identity.infrastructure.epoch_cache import RedisEpochStore
from saber_uli.identity.infrastructure.session_revocations import RedisSessionRevocations
from saber_uli.identity.infrastructure.tokens import AccessTokenCodec, RefreshTokenFactory
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.api.consent_guard import require_consent
from saber_uli.shared.api.health import router as health_router
from saber_uli.shared.api.middleware import PathScopedMiddleware, RequestLoggingMiddleware
from saber_uli.shared.api.problems import install_problem_handlers
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import Clock, SystemClock
from saber_uli.shared.infrastructure.db import create_engine, create_session_factory
from saber_uli.shared.infrastructure.logging import configure_logging
from saber_uli.shared.infrastructure.rate_limit import RateLimiter

OIDC_PREFIX = "/api/auth/microsoft"
OIDC_COOKIE = "su_oidc"


def _derived_key(secret: str, purpose: str) -> bytes:
    """Clave HMAC derivada para un propósito; nunca se usa el secreto tal cual."""
    return hmac.new(secret.encode(), purpose.encode(), hashlib.sha256).digest()


def create_app(
    settings: Settings | None = None,
    *,
    clock: Clock | None = None,
    log_stream: TextIO | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    clock = clock or SystemClock()
    configure_logging(settings.log_level, stream=log_stream)

    redis_url = settings.redis_url.get_secret_value()
    engine = create_engine(settings.database_url.get_secret_value())
    session_factory = create_session_factory(engine)
    readiness_redis = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
    bus = EventBus()

    def identity_uow() -> SqlAlchemyIdentityUnitOfWork:
        return SqlAlchemyIdentityUnitOfWork(session_factory, bus)

    epochs = RedisEpochStore(redis_url)
    revocations = RedisSessionRevocations(redis_url)
    codec = AccessTokenCodec(
        {settings.jwt_key_id: settings.jwt_signing_key.get_secret_value().encode()},
        active_kid=settings.jwt_key_id,
    )
    cookie_secret = settings.session_cookie_secret.get_secret_value()

    async def invalidate_epoch(event: UserAccessChanged) -> None:
        await epochs.invalidate(event.user_id)

    bus.subscribe(UserAccessChanged, invalidate_epoch, phase="after_commit")

    async def database_ready() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def redis_ready() -> None:
        await readiness_redis.ping()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()
        await readiness_redis.aclose()
        await epochs.close()
        await revocations.close()

    app = FastAPI(
        title="Saber Uli API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,  # el contrato publicado es specs/001-identidad-acceso/contracts
    )
    app.state.settings = settings
    app.state.clock = clock
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.event_bus = bus
    app.state.rate_limiter = RateLimiter(
        redis_url, hash_key=_derived_key(cookie_secret, "saber-uli/rate-limit-email")
    )
    app.state.authenticator = AccessGuard(
        decoder=codec,
        epochs=epochs,
        revocations=revocations,
        uow_factory=identity_uow,
        clock=clock,
    )
    app.state.consent_checker = ConsentStatusQuery(uow_factory=identity_uow, clock=clock)
    app.state.session_service = SessionService(
        uow_factory=identity_uow,
        clock=clock,
        access_tokens=codec,
        refresh_tokens=RefreshTokenFactory(),
        revocations=revocations,
    )
    app.state.entra_client = EntraIdClient(
        authority=settings.entra_authority,
        tenant_id=settings.entra_tenant_id,
        client_id=str(settings.entra_client_id),
        client_secret=settings.entra_client_secret.get_secret_value(),
        redirect_uri=f"{settings.public_base_url}/api/auth/microsoft/callback",
    )
    app.state.authenticate_institutional = AuthenticateInstitutionalUser(
        uow_factory=identity_uow, clock=clock, tenant_id=settings.entra_tenant_id
    )
    app.state.get_me = GetMe(uow_factory=identity_uow, clock=clock)
    app.state.consent_service = ConsentService(uow_factory=identity_uow, clock=clock)
    app.state.privacy_policy_service = PrivacyPolicyService(uow_factory=identity_uow, clock=clock)
    app.state.readiness_checks = {"database": database_ready, "redis": redis_ready}

    install_problem_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(microsoft_router)
    # Toda ruta de /api/v1 pasa por la guardia de autorización de datos (FR-014).
    v1 = [Depends(require_consent)]
    app.include_router(me_router, dependencies=v1)
    app.include_router(consent_router, dependencies=v1)
    app.include_router(policy_router, dependencies=v1)

    # Sesión firmada (state, nonce, PKCE) solo para el flujo OIDC (R-13), 10 minutos.
    app.add_middleware(
        PathScopedMiddleware,
        prefix=OIDC_PREFIX,
        middleware=SessionMiddleware,
        options={
            "secret_key": _derived_key(cookie_secret, "saber-uli/oidc-session").hex(),
            "session_cookie": OIDC_COOKIE,
            "max_age": 600,
            "path": OIDC_PREFIX,
            "same_site": "lax",
            "https_only": settings.public_base_url.startswith("https://"),
        },
    )
    app.add_middleware(RequestLoggingMiddleware)
    return app
