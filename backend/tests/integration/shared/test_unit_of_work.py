"""T025: unidad de trabajo con SQLAlchemy y despacho de eventos en dos fases (R-08)."""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.application.unit_of_work import UnitOfWork
from saber_uli.shared.domain.events import DomainEvent
from saber_uli.shared.infrastructure.db import SqlAlchemyUnitOfWork, create_session_factory

NOON = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)

MakeUow = Callable[[], SqlAlchemyUnitOfWork]


@dataclass(frozen=True, kw_only=True)
class FilaCreada(DomainEvent):
    event_type: ClassVar[str] = "shared.FilaCreada"
    row_id: int


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def probe_schema(database_urls: dict[str, str]) -> AsyncIterator[None]:
    engine = create_async_engine(database_urls["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS test_uow CASCADE"))
        await conn.execute(text("CREATE SCHEMA test_uow"))
        await conn.execute(text("CREATE TABLE test_uow.probe (id int PRIMARY KEY)"))
        await conn.execute(text("GRANT USAGE ON SCHEMA test_uow TO saber_app"))
        await conn.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON test_uow.probe TO saber_app")
        )
    yield
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA test_uow CASCADE"))
    await engine.dispose()


@pytest.fixture
async def clean_probe(probe_schema: None, app_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with app_engine.begin() as conn:
        await conn.execute(text("DELETE FROM test_uow.probe"))


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def session_factory(app_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(app_engine)


@pytest.fixture
def make_uow(session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> MakeUow:
    return lambda: SqlAlchemyUnitOfWork(session_factory, bus)


async def ids(engine: AsyncEngine) -> list[int]:
    """Lee desde una conexión independiente: solo ve lo confirmado."""
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT id FROM test_uow.probe ORDER BY id"))
        return list(rows.scalars())


async def insert(uow: SqlAlchemyUnitOfWork, row_id: int) -> None:
    await uow.session.execute(text("INSERT INTO test_uow.probe VALUES (:id)"), {"id": row_id})


pytestmark = pytest.mark.usefixtures("clean_probe")


async def test_commit_persiste(make_uow: MakeUow, app_engine: AsyncEngine) -> None:
    async with make_uow() as uow:
        await insert(uow, 1)
        await uow.commit()

    assert await ids(app_engine) == [1]


async def test_una_excepcion_revierte_y_se_propaga(
    make_uow: MakeUow, app_engine: AsyncEngine
) -> None:
    with pytest.raises(RuntimeError):
        async with make_uow() as uow:
            await insert(uow, 1)
            raise RuntimeError("algo falló")

    assert await ids(app_engine) == []


async def test_salir_sin_commit_revierte(make_uow: MakeUow, app_engine: AsyncEngine) -> None:
    async with make_uow() as uow:
        await insert(uow, 1)

    assert await ids(app_engine) == []


async def test_in_transaction_confirma_junto_con_la_accion(
    make_uow: MakeUow, bus: EventBus, app_engine: AsyncEngine
) -> None:
    async def write_more(event: FilaCreada, uow: UnitOfWork) -> None:
        assert isinstance(uow, SqlAlchemyUnitOfWork)
        await insert(uow, event.row_id + 100)

    bus.subscribe(FilaCreada, write_more, phase="in_transaction")

    async with make_uow() as uow:
        await insert(uow, 1)
        uow.record(FilaCreada(occurred_at=NOON, row_id=1))
        await uow.commit()

    assert await ids(app_engine) == [1, 101]


async def test_un_fallo_in_transaction_revierte_todo(
    make_uow: MakeUow, bus: EventBus, app_engine: AsyncEngine
) -> None:
    after: list[DomainEvent] = []

    async def write_then_fail(event: FilaCreada, uow: UnitOfWork) -> None:
        assert isinstance(uow, SqlAlchemyUnitOfWork)
        await insert(uow, 101)
        raise RuntimeError("el outbox falló")

    async def after_commit(event: DomainEvent) -> None:
        after.append(event)

    bus.subscribe(FilaCreada, write_then_fail, phase="in_transaction")
    bus.subscribe(FilaCreada, after_commit, phase="after_commit")

    with pytest.raises(RuntimeError, match="outbox"):
        async with make_uow() as uow:
            await insert(uow, 1)
            uow.record(FilaCreada(occurred_at=NOON, row_id=1))
            await uow.commit()

    assert await ids(app_engine) == []
    assert after == []


async def test_after_commit_corre_despues_del_commit(
    make_uow: MakeUow, bus: EventBus, app_engine: AsyncEngine
) -> None:
    seen_from_other_connection: list[list[int]] = []

    async def check(event: DomainEvent) -> None:
        seen_from_other_connection.append(await ids(app_engine))

    bus.subscribe(FilaCreada, check, phase="after_commit")

    async with make_uow() as uow:
        await insert(uow, 7)
        uow.record(FilaCreada(occurred_at=NOON, row_id=7))
        await uow.commit()

    assert seen_from_other_connection == [[7]]


async def test_tras_un_rollback_no_corre_after_commit(make_uow: MakeUow, bus: EventBus) -> None:
    after: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        after.append(event)

    bus.subscribe(FilaCreada, handler, phase="after_commit")

    async with make_uow() as uow:
        uow.record(FilaCreada(occurred_at=NOON, row_id=1))
        await uow.rollback()
        await uow.commit()  # ya no hay eventos pendientes

    assert after == []


async def test_un_fallo_after_commit_no_deshace_el_commit(
    make_uow: MakeUow, bus: EventBus, app_engine: AsyncEngine
) -> None:
    async def boom(event: DomainEvent) -> None:
        raise RuntimeError("Redis caído")

    bus.subscribe(FilaCreada, boom, phase="after_commit")

    async with make_uow() as uow:
        await insert(uow, 3)
        uow.record(FilaCreada(occurred_at=NOON, row_id=3))
        await uow.commit()

    assert await ids(app_engine) == [3]


async def test_un_segundo_commit_no_vuelve_a_despachar(make_uow: MakeUow, bus: EventBus) -> None:
    calls: list[str] = []

    async def in_tx(event: DomainEvent, uow: UnitOfWork) -> None:
        calls.append("in")

    async def after(event: DomainEvent) -> None:
        calls.append("after")

    bus.subscribe(FilaCreada, in_tx, phase="in_transaction")
    bus.subscribe(FilaCreada, after, phase="after_commit")

    async with make_uow() as uow:
        uow.record(FilaCreada(occurred_at=NOON, row_id=1))
        await uow.commit()
        await uow.commit()

    assert calls == ["in", "after"]


async def test_registrar_eventos_desde_in_transaction_es_un_error(
    make_uow: MakeUow, bus: EventBus
) -> None:
    async def cascade(event: FilaCreada, uow: UnitOfWork) -> None:
        uow.record(FilaCreada(occurred_at=NOON, row_id=event.row_id + 1))

    bus.subscribe(FilaCreada, cascade, phase="in_transaction")

    with pytest.raises(RuntimeError):
        async with make_uow() as uow:
            uow.record(FilaCreada(occurred_at=NOON, row_id=1))
            await uow.commit()
