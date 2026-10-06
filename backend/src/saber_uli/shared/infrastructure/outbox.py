"""Outbox transaccional (research R-08; ADR 0004; data-model §3.1).

- Escritor: `register_outbox(bus, *eventos, context=...)` suscribe en la fase `in_transaction`
  del bus un manejador que inserta el evento en `shared.outbox_events` con la misma sesión que la
  acción: se confirma si y solo si la acción se confirma. El `id` de la fila es el `event_id`
  (clave de idempotencia). El payload lleva solo identificadores; claves de nombre, correo,
  token o secreto lanzan `PersonalDataInOutboxError` y revierten la acción.
- Despachador: `OutboxDispatcher.dispatch_once()` reclama un lote con `FOR UPDATE SKIP LOCKED`
  (varios despachadores no se pisan), entrega cada evento a sus manejadores y lo marca procesado;
  si un manejador falla, reintenta con espera exponencial (5 s · 2^(n−1), máx. 1 h) y guarda en
  `last_error` solo la clase de la excepción. Entrega al menos una vez: los manejadores deben
  deduplicar por `event_id`.
- Purga: `purge_processed()` borra lo procesado hace más de 7 días.
"""

import dataclasses
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import DateTime, Integer, Text, Uuid, delete, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.application.unit_of_work import UnitOfWork
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.events import DomainEvent
from saber_uli.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork

RETENTION = timedelta(days=7)
BASE_BACKOFF = timedelta(seconds=5)
MAX_BACKOFF = timedelta(hours=1)

_log = structlog.get_logger(__name__)


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"
    __table_args__ = ({"schema": "shared"},)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    context: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class PersonalDataInOutboxError(ValueError):
    """El payload contiene datos personales o secretos (solo se admiten identificadores)."""


_FORBIDDEN_KEYS = frozenset({"name", "nombre", "display_name", "code"})
_FORBIDDEN_FRAGMENTS = ("email", "correo", "token", "password", "secret")


def _check_key(key: str) -> None:
    normalized = key.lower().replace("-", "_")
    if normalized in _FORBIDDEN_KEYS or any(f in normalized for f in _FORBIDDEN_FRAGMENTS):
        raise PersonalDataInOutboxError(f"clave no permitida en el outbox: {key!r}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        for key in value:
            _check_key(str(key))
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_jsonable(v) for v in value]
    return value


def event_payload(event: DomainEvent) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in dataclasses.fields(event):
        if field.name in ("event_id", "occurred_at"):
            continue
        _check_key(field.name)
        payload[field.name] = _jsonable(getattr(event, field.name))
    return payload


def register_outbox(bus: EventBus, *event_types: type[DomainEvent], context: str) -> None:
    """Hace que esos eventos se escriban en el outbox dentro de la transacción de la acción."""

    async def append(event: DomainEvent, uow: UnitOfWork) -> None:
        if not isinstance(uow, SqlAlchemyUnitOfWork):
            raise TypeError("el outbox necesita una unidad de trabajo de SQLAlchemy")
        uow.session.add(
            OutboxEventRow(
                id=event.event_id,
                context=context,
                event_type=event.event_type,
                payload=event_payload(event),
                occurred_at=event.occurred_at,
                available_at=event.occurred_at,
                attempts=0,
            )
        )
        await uow.session.flush()

    for event_type in event_types:
        bus.subscribe(event_type, append, phase="in_transaction")


@dataclasses.dataclass(frozen=True)
class OutboxMessage:
    event_id: UUID
    event_type: str
    context: str
    payload: Mapping[str, Any]
    occurred_at: datetime
    attempt: int


OutboxHandler = Callable[[OutboxMessage], Awaitable[None]]


class OutboxRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[OutboxHandler]] = defaultdict(list)

    def register(self, event_type: str, handler: OutboxHandler) -> None:
        self._handlers[event_type].append(handler)

    def handlers(self, event_type: str) -> list[OutboxHandler]:
        return list(self._handlers.get(event_type, ()))


def backoff(attempts: int) -> timedelta:
    return min(BASE_BACKOFF * 2 ** max(attempts - 1, 0), MAX_BACKOFF)


class OutboxDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: OutboxRegistry,
        *,
        clock: Clock,
        batch_size: int = 50,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry
        self._clock = clock
        self._batch_size = batch_size

    async def dispatch_once(self) -> int:
        """Procesa un lote disponible; devuelve cuántos eventos reclamó."""
        now = self._clock.now()
        async with self._session_factory() as db, db.begin():
            rows = (
                await db.scalars(
                    select(OutboxEventRow)
                    .where(OutboxEventRow.processed_at.is_(None))
                    .where(OutboxEventRow.available_at <= now)
                    .order_by(OutboxEventRow.available_at, OutboxEventRow.id)
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                await self._deliver(row, now)
        return len(rows)

    async def _deliver(self, row: OutboxEventRow, now: datetime) -> None:
        message = OutboxMessage(
            event_id=row.id,
            event_type=row.event_type,
            context=row.context,
            payload=row.payload,
            occurred_at=row.occurred_at,
            attempt=row.attempts + 1,
        )
        try:
            for handler in self._registry.handlers(row.event_type):
                await handler(message)
        except Exception as error:
            row.attempts += 1
            row.available_at = now + backoff(row.attempts)
            row.last_error = type(error).__name__  # nunca el mensaje: podría tener datos personales
            _log.warning(
                "outbox_delivery_failed",
                event_type=row.event_type,
                event_id=str(row.id),
                attempts=row.attempts,
                error_type=row.last_error,
            )
        else:
            row.processed_at = now

    async def purge_processed(self) -> int:
        cutoff = self._clock.now() - RETENTION
        async with self._session_factory() as db, db.begin():
            result = await db.execute(
                delete(OutboxEventRow).where(OutboxEventRow.processed_at < cutoff)
            )
        return int(getattr(result, "rowcount", 0) or 0)
