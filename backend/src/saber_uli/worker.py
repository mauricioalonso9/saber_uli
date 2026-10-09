"""Worker y Beat de Celery sobre Redis (research R-08, R-09; T034).

    celery -A saber_uli.worker worker
    celery -A saber_uli.worker beat --scheduler saber_uli.worker:HeartbeatScheduler

Tareas programadas (zona America/Bogota):

- `dispatch_outbox`: cada 5 s (aquí).
- `expire_invitations`: cada hora (T131).
- `process_retention`: diaria a las 02:00 (avisos y supresiones automáticas, US7).
- `process_deletion_requests`: cada 15 min (respaldo del outbox, US7).
- `purge_expired_auth_artifacts`: diaria a las 03:30; purga el outbox aquí y las sesiones y
  enlaces vencidos en US4/US7.

Al importar el módulo solo se lee `REDIS_URL` (el broker). La configuración completa se carga
dentro de cada tarea, así las pruebas importan el módulo sin entorno.
"""

import asyncio
import os
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from celery import Celery, signals
from celery.beat import PersistentScheduler
from celery.schedules import crontab

from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.logging import configure_logging

_log = structlog.get_logger(__name__)

celery_app = Celery("saber_uli")
celery_app.conf.update(
    broker_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    timezone="America/Bogota",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    beat_schedule={
        "dispatch-outbox": {
            "task": "saber_uli.dispatch_outbox",
            "schedule": timedelta(seconds=5),
            "options": {"expires": 5},
        },
        "expire-invitations": {
            "task": "saber_uli.expire_invitations",
            "schedule": crontab(minute=0),
        },
        "process-retention": {
            "task": "saber_uli.process_retention",
            "schedule": crontab(hour=2, minute=0),
        },
        "process-deletion-requests": {
            "task": "saber_uli.process_deletion_requests",
            "schedule": timedelta(minutes=15),
        },
        "purge-expired-auth-artifacts": {
            "task": "saber_uli.purge_expired_auth_artifacts",
            "schedule": crontab(hour=3, minute=30),
        },
    },
)
app = celery_app  # nombre que busca `celery -A saber_uli.worker`


@signals.setup_logging.connect
def _setup_logging(**_: Any) -> None:
    """Logs JSON sin datos personales también en el worker y en Beat (R-23)."""
    configure_logging(os.environ.get("LOG_LEVEL", "INFO"))


class HeartbeatScheduler(PersistentScheduler):
    """Scheduler de Beat que actualiza un archivo de latido en cada ciclo; el health check de
    Compose lo considera enfermo si pasan más de 2 minutos sin latido."""

    def tick(self, *args: Any, **kwargs: Any) -> Any:
        path = Path(os.environ.get("BEAT_HEARTBEAT_FILE", "/tmp/beat-heartbeat"))  # noqa: S108
        path.touch()
        return super().tick(*args, **kwargs)


# --- Outbox ------------------------------------------------------------------------------------


def outbox_registry(session_factory: Any) -> Any:
    """Manejadores del outbox por tipo de evento. Cada historia agrega los suyos (US4, US7…)."""
    from saber_uli.config import get_settings
    from saber_uli.identity.application.erase_user import EraseUser
    from saber_uli.identity.infrastructure.handlers.link_emails import LinkEmailHandlers
    from saber_uli.identity.infrastructure.handlers.retention_notice import (
        RetentionNoticeHandler,
    )
    from saber_uli.identity.infrastructure.link_tokens import LinkTokenFactory
    from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
    from saber_uli.notifications.application.public import EmailService
    from saber_uli.notifications.infrastructure.smtp import SmtpEmailSender
    from saber_uli.notifications.infrastructure.templates import JinjaTemplateRenderer
    from saber_uli.shared.application.event_bus import EventBus
    from saber_uli.shared.infrastructure.outbox import OutboxMessage, OutboxRegistry

    settings = get_settings()
    bus = EventBus()
    registry = OutboxRegistry()
    email = EmailService(
        renderer=JinjaTemplateRenderer(public_base_url=settings.public_base_url),
        sender=SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            sender=settings.smtp_from,
            user=settings.smtp_user,
            password=(
                settings.smtp_password.get_secret_value() if settings.smtp_password else None
            ),
            starttls=settings.smtp_starttls,
        ),
    )
    LinkEmailHandlers(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
        email=email,
        clock=SystemClock(),
        tokens=LinkTokenFactory(),
    ).register(registry)
    RetentionNoticeHandler(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
        email=email,
        clock=SystemClock(),
    ).register(registry)

    # La supresión publica `UserErased` (outbox) y cambia la época de autorización.
    erase_bus = identity_task_bus(settings.redis_url.get_secret_value())
    erase = EraseUser(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, erase_bus),
        clock=SystemClock(),
    )

    async def on_deletion_requested(message: OutboxMessage) -> None:
        await erase.execute(UUID(str(message.payload["deletion_request_id"])))

    registry.register("identity.DeletionRequested", on_deletion_requested)
    return registry


def identity_task_bus(redis_url: str) -> Any:
    """Bus de las tareas que cambian cuentas: escribe sus eventos en el outbox e invalida la
    caché de `auth_epoch` tras el commit (R-16)."""
    from saber_uli.identity.domain.events import UserAccessChanged
    from saber_uli.identity.infrastructure.epoch_cache import RedisEpochStore
    from saber_uli.identity.infrastructure.outbox_events import register_identity_outbox
    from saber_uli.shared.application.event_bus import EventBus

    bus = EventBus()
    register_identity_outbox(bus)

    async def invalidate_epoch(event: UserAccessChanged) -> None:
        epochs = RedisEpochStore(redis_url)
        try:
            await epochs.invalidate(event.user_id)
        finally:
            await epochs.close()

    bus.subscribe(UserAccessChanged, invalidate_epoch, phase="after_commit")
    return bus


async def _with_dispatcher(action: str) -> int:
    """Abre un motor propio (cada tarea corre en su propio bucle) y ejecuta `action`."""
    from saber_uli.config import get_settings
    from saber_uli.shared.infrastructure.db import (
        create_engine,
        create_session_factory,
    )
    from saber_uli.shared.infrastructure.outbox import OutboxDispatcher

    engine = create_engine(get_settings().database_url.get_secret_value())
    try:
        session_factory = create_session_factory(engine)
        dispatcher = OutboxDispatcher(
            session_factory, outbox_registry(session_factory), clock=SystemClock()
        )
        if action == "purge":
            return await dispatcher.purge_processed()
        return await dispatcher.dispatch_once()
    finally:
        await engine.dispose()


@celery_app.task(name="saber_uli.dispatch_outbox")
def dispatch_outbox() -> int:
    return asyncio.run(_with_dispatcher("dispatch"))


@celery_app.task(name="saber_uli.purge_expired_auth_artifacts")
def purge_expired_auth_artifacts() -> int:
    purged = asyncio.run(_with_dispatcher("purge"))
    _log.info("outbox_purged", count=purged)
    return purged


# --- Tareas que completan las historias --------------------------------------------------------


async def _expire_invitations() -> None:
    from saber_uli.config import get_settings
    from saber_uli.identity.domain.events import UserAccessChanged
    from saber_uli.identity.infrastructure.epoch_cache import RedisEpochStore
    from saber_uli.identity.infrastructure.tasks import expire_invitations as run
    from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
    from saber_uli.shared.application.event_bus import EventBus
    from saber_uli.shared.infrastructure.db import create_engine, create_session_factory

    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())
    epochs = RedisEpochStore(settings.redis_url.get_secret_value())
    try:
        session_factory = create_session_factory(engine)
        bus = EventBus()

        async def invalidate_epoch(event: UserAccessChanged) -> None:
            await epochs.invalidate(event.user_id)

        bus.subscribe(UserAccessChanged, invalidate_epoch, phase="after_commit")
        await run(
            uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
            clock=SystemClock(),
        )
    finally:
        await epochs.close()
        await engine.dispose()


@celery_app.task(name="saber_uli.expire_invitations")
def expire_invitations() -> None:
    asyncio.run(_expire_invitations())


async def _identity_task(name: str) -> None:
    from saber_uli.config import get_settings
    from saber_uli.identity.infrastructure import tasks
    from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
    from saber_uli.shared.infrastructure.db import create_engine, create_session_factory

    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        session_factory = create_session_factory(engine)
        bus = identity_task_bus(settings.redis_url.get_secret_value())
        run = getattr(tasks, name)
        await run(
            uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
            clock=SystemClock(),
        )
    finally:
        await engine.dispose()


@celery_app.task(name="saber_uli.process_retention")
def process_retention() -> None:
    asyncio.run(_identity_task("process_retention"))


@celery_app.task(name="saber_uli.process_deletion_requests")
def process_deletion_requests() -> None:
    asyncio.run(_identity_task("process_deletion_requests"))
