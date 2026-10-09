"""T025: bus de eventos en proceso con dos fases (research R-08, precisión 2026-10-06)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ClassVar

import pytest
from structlog.testing import capture_logs

from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.events import DomainEvent

NOON = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


@dataclass(frozen=True, kw_only=True)
class CuentaCambio(DomainEvent):
    event_type: ClassVar[str] = "identity.CuentaCambio"


@dataclass(frozen=True, kw_only=True)
class CuentaDesactivada(CuentaCambio):
    event_type: ClassVar[str] = "identity.CuentaDesactivada"


@dataclass(frozen=True, kw_only=True)
class OtroEvento(DomainEvent):
    event_type: ClassVar[str] = "identity.OtroEvento"


UOW: Any = object()  # los manejadores de esta prueba no usan la unidad de trabajo


async def test_un_manejador_de_una_clase_base_recibe_las_subclases() -> None:
    bus = EventBus()
    seen: list[str] = []

    async def handler(event: CuentaCambio, uow: Any) -> None:
        seen.append(event.event_type)

    bus.subscribe(CuentaCambio, handler, phase="in_transaction")
    await bus.dispatch_in_transaction(
        [CuentaDesactivada(occurred_at=NOON), OtroEvento(occurred_at=NOON)], UOW
    )

    assert seen == ["identity.CuentaDesactivada"]


async def test_los_manejadores_corren_en_orden_de_suscripcion() -> None:
    bus = EventBus()
    order: list[int] = []

    def make(n: int) -> Any:
        async def handler(event: DomainEvent) -> None:
            order.append(n)

        return handler

    for n in (1, 2, 3):
        bus.subscribe(DomainEvent, make(n), phase="after_commit")
    await bus.dispatch_after_commit([OtroEvento(occurred_at=NOON)])

    assert order == [1, 2, 3]


async def test_cada_fase_solo_ejecuta_sus_manejadores() -> None:
    bus = EventBus()
    calls: list[str] = []

    async def in_tx(event: DomainEvent, uow: Any) -> None:
        calls.append("in_transaction")

    async def after(event: DomainEvent) -> None:
        calls.append("after_commit")

    bus.subscribe(DomainEvent, in_tx, phase="in_transaction")
    bus.subscribe(DomainEvent, after, phase="after_commit")

    await bus.dispatch_in_transaction([OtroEvento(occurred_at=NOON)], UOW)
    assert calls == ["in_transaction"]
    await bus.dispatch_after_commit([OtroEvento(occurred_at=NOON)])
    assert calls == ["in_transaction", "after_commit"]


async def test_un_fallo_in_transaction_se_propaga() -> None:
    bus = EventBus()

    async def boom(event: DomainEvent, uow: Any) -> None:
        raise RuntimeError("falla")

    bus.subscribe(DomainEvent, boom, phase="in_transaction")

    with pytest.raises(RuntimeError):
        await bus.dispatch_in_transaction([OtroEvento(occurred_at=NOON)], UOW)


async def test_un_fallo_after_commit_se_registra_y_no_detiene_a_los_demas() -> None:
    bus = EventBus()
    reached: list[str] = []
    event = OtroEvento(occurred_at=NOON)

    async def boom(event: DomainEvent) -> None:
        raise ValueError("detalle con ana@unilibre.edu.co")

    async def next_handler(event: DomainEvent) -> None:
        reached.append("siguiente")

    bus.subscribe(DomainEvent, boom, phase="after_commit")
    bus.subscribe(DomainEvent, next_handler, phase="after_commit")

    with capture_logs() as logs:
        await bus.dispatch_after_commit([event])

    assert reached == ["siguiente"]
    [entry] = logs
    assert entry["event"] == "after_commit_handler_failed"
    assert entry["event_type"] == "identity.OtroEvento"
    assert entry["event_id"] == str(event.event_id)
    assert entry["error_type"] == "ValueError"
    # Solo identificadores y la clase de la excepción: nunca su mensaje.
    assert "ana@unilibre.edu.co" not in repr(entry)


def test_fase_invalida() -> None:
    bus = EventBus()

    async def handler(event: DomainEvent) -> None:
        pass

    with pytest.raises(ValueError):
        bus.subscribe(DomainEvent, handler, phase="despues")  # type: ignore[arg-type]
