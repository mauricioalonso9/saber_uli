"""T031: outbox transaccional (research R-08; ADR 0004; data-model §3.1)."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.domain.events import DomainEvent
from saber_uli.shared.infrastructure.db import SqlAlchemyUnitOfWork, create_session_factory
from saber_uli.shared.infrastructure.outbox import (
    OutboxDispatcher,
    OutboxMessage,
    OutboxRegistry,
    PersonalDataInOutboxError,
    register_outbox,
)

T0 = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


@dataclass(frozen=True, kw_only=True)
class InvitacionCreada(DomainEvent):
    event_type: ClassVar[str] = "identity.InvitationCreated"
    invitation_id: UUID


@dataclass(frozen=True, kw_only=True)
class EventoConCorreo(DomainEvent):
    event_type: ClassVar[str] = "identity.EventoConCorreo"
    email: str


@dataclass(frozen=True, kw_only=True)
class EventoConToken(DomainEvent):
    event_type: ClassVar[str] = "identity.EventoConToken"
    access_token: str


@pytest.fixture
async def clean_outbox(app_engine: AsyncEngine) -> AsyncIterator[None]:
    async with app_engine.begin() as conn:
        await conn.execute(text("DELETE FROM shared.outbox_events"))
    yield
    async with app_engine.begin() as conn:
        await conn.execute(text("DELETE FROM shared.outbox_events"))


pytestmark = pytest.mark.usefixtures("clean_outbox")


@pytest.fixture
def bus() -> EventBus:
    bus = EventBus()
    register_outbox(bus, InvitacionCreada, EventoConCorreo, EventoConToken, context="identity")
    return bus


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


async def write(app_engine: AsyncEngine, bus: EventBus, *events: DomainEvent) -> None:
    async with SqlAlchemyUnitOfWork(create_session_factory(app_engine), bus) as uow:
        uow.record(*events)
        await uow.commit()


async def outbox_rows(app_engine: AsyncEngine) -> list[Any]:
    async with app_engine.connect() as conn:
        result = await conn.execute(
            text(
                """SELECT id, context, event_type, payload, occurred_at, available_at, attempts,
                          processed_at, last_error
                   FROM shared.outbox_events ORDER BY occurred_at, id"""
            )
        )
        return list(result.all())


def event(n: int = 0) -> InvitacionCreada:
    return InvitacionCreada(occurred_at=T0 + timedelta(seconds=n), invitation_id=uuid4())


# --- Escritura ---------------------------------------------------------------------------------


async def test_el_evento_se_escribe_en_la_misma_transaccion(
    app_engine: AsyncEngine, bus: EventBus
) -> None:
    created = event()
    await write(app_engine, bus, created)

    [row] = await outbox_rows(app_engine)
    assert row.id == created.event_id  # clave de idempotencia
    assert (row.context, row.event_type) == ("identity", "identity.InvitationCreated")
    assert row.payload == {"invitation_id": str(created.invitation_id)}
    assert row.occurred_at == row.available_at == T0
    assert (row.attempts, row.processed_at, row.last_error) == (0, None, None)


async def test_un_rollback_no_deja_evento(app_engine: AsyncEngine, bus: EventBus) -> None:
    with pytest.raises(RuntimeError):
        async with SqlAlchemyUnitOfWork(create_session_factory(app_engine), bus) as uow:
            uow.record(event())
            raise RuntimeError("la acción falló")

    assert await outbox_rows(app_engine) == []


@pytest.mark.parametrize(
    "bad",
    [
        EventoConCorreo(occurred_at=T0, email="ana@unilibre.edu.co"),
        EventoConToken(occurred_at=T0, access_token="secreto"),
    ],
)
async def test_rechaza_payload_con_datos_personales_o_tokens(
    app_engine: AsyncEngine, bus: EventBus, bad: DomainEvent
) -> None:
    with pytest.raises(PersonalDataInOutboxError):
        await write(app_engine, bus, bad)

    assert await outbox_rows(app_engine) == []


# --- Despacho ----------------------------------------------------------------------------------


def dispatcher(
    app_engine: AsyncEngine, registry: OutboxRegistry, clock: FixedClock
) -> OutboxDispatcher:
    return OutboxDispatcher(create_session_factory(app_engine), registry, clock=clock)


async def test_despacha_y_marca_procesado_una_sola_vez(
    app_engine: AsyncEngine, bus: EventBus, clock: FixedClock
) -> None:
    created = event()
    await write(app_engine, bus, created)
    received: list[OutboxMessage] = []
    registry = OutboxRegistry()

    async def handler(message: OutboxMessage) -> None:
        received.append(message)

    registry.register("identity.InvitationCreated", handler)

    assert await dispatcher(app_engine, registry, clock).dispatch_once() == 1
    assert await dispatcher(app_engine, registry, clock).dispatch_once() == 0

    [message] = received
    assert message.event_id == created.event_id
    assert message.payload == {"invitation_id": str(created.invitation_id)}
    [row] = await outbox_rows(app_engine)
    assert row.processed_at == T0


async def test_dos_despachadores_concurrentes_no_entregan_dos_veces(
    app_engine: AsyncEngine, bus: EventBus, clock: FixedClock
) -> None:
    events = [event(n) for n in range(30)]
    await write(app_engine, bus, *events)
    clock.set(T0 + timedelta(minutes=1))  # todos disponibles
    delivered: list[UUID] = []
    registry = OutboxRegistry()

    async def slow(message: OutboxMessage) -> None:
        await asyncio.sleep(0.01)
        delivered.append(message.event_id)

    registry.register("identity.InvitationCreated", slow)
    first = OutboxDispatcher(
        create_session_factory(app_engine), registry, clock=clock, batch_size=10
    )
    second = OutboxDispatcher(
        create_session_factory(app_engine), registry, clock=clock, batch_size=10
    )

    for _ in range(3):
        await asyncio.gather(first.dispatch_once(), second.dispatch_once())

    assert sorted(delivered) == sorted(e.event_id for e in events)
    assert len(delivered) == len(set(delivered))


async def test_reintento_con_espera_y_error_sin_datos_personales(
    app_engine: AsyncEngine, bus: EventBus, clock: FixedClock
) -> None:
    created = event()
    await write(app_engine, bus, created)
    calls: list[UUID] = []
    registry = OutboxRegistry()

    async def flaky(message: OutboxMessage) -> None:
        calls.append(message.event_id)
        if len(calls) == 1:
            raise ValueError("no se pudo enviar a ana@unilibre.edu.co")

    registry.register("identity.InvitationCreated", flaky)
    worker = dispatcher(app_engine, registry, clock)

    await worker.dispatch_once()
    [failed] = await outbox_rows(app_engine)
    assert failed.attempts == 1
    assert failed.processed_at is None
    assert failed.last_error == "ValueError"
    assert failed.available_at > T0

    assert await worker.dispatch_once() == 0  # todavía en espera
    clock.set(failed.available_at)
    assert await worker.dispatch_once() == 1

    # El mismo event_id llega en el reintento: los manejadores deduplican por él.
    assert calls == [created.event_id, created.event_id]
    [done] = await outbox_rows(app_engine)
    assert done.processed_at == failed.available_at


async def test_la_espera_crece_con_cada_intento(
    app_engine: AsyncEngine, bus: EventBus, clock: FixedClock
) -> None:
    await write(app_engine, bus, event())
    registry = OutboxRegistry()

    async def always_fails(message: OutboxMessage) -> None:
        raise RuntimeError("falla")

    registry.register("identity.InvitationCreated", always_fails)
    worker = dispatcher(app_engine, registry, clock)
    waits: list[timedelta] = []
    for _ in range(4):
        await worker.dispatch_once()
        [row] = await outbox_rows(app_engine)
        waits.append(row.available_at - clock.now())
        clock.set(row.available_at)

    assert waits == sorted(waits)
    assert waits[0] < waits[-1]


async def test_un_evento_sin_manejador_se_marca_procesado(
    app_engine: AsyncEngine, bus: EventBus, clock: FixedClock
) -> None:
    await write(app_engine, bus, event())

    assert await dispatcher(app_engine, OutboxRegistry(), clock).dispatch_once() == 1
    [row] = await outbox_rows(app_engine)
    assert row.processed_at == T0


# --- Purga -------------------------------------------------------------------------------------


async def test_purga_lo_procesado_hace_mas_de_7_dias(
    app_engine: AsyncEngine, bus: EventBus, clock: FixedClock
) -> None:
    old, recent, pending = event(1), event(2), event(3)
    await write(app_engine, bus, old, recent, pending)
    async with app_engine.begin() as conn:
        await conn.execute(
            text("UPDATE shared.outbox_events SET processed_at = :t WHERE id = :id"),
            {"t": T0 - timedelta(days=8), "id": old.event_id},
        )
        await conn.execute(
            text("UPDATE shared.outbox_events SET processed_at = :t WHERE id = :id"),
            {"t": T0 - timedelta(days=6), "id": recent.event_id},
        )

    purged = await dispatcher(app_engine, OutboxRegistry(), clock).purge_processed()

    assert purged == 1
    assert {row.id for row in await outbox_rows(app_engine)} == {recent.event_id, pending.event_id}
