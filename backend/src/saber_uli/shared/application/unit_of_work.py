"""Unidad de trabajo (puerto). La implementación con SQLAlchemy está en
`saber_uli.shared.infrastructure.db.SqlAlchemyUnitOfWork`.

Uso:

    async with uow:
        ...            # cambios y uow.record(evento)
        await uow.commit()

Al salir del bloque siempre se revierte lo no confirmado: con una excepción (que se propaga) o
sin haber llamado a `commit()`. El commit es explícito.
"""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.events import DomainEvent


class UnitOfWork(ABC):
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._events: list[DomainEvent] = []
        self._dispatching = False

    async def __aenter__(self) -> Self:
        await self._begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await self.rollback()
        finally:
            await self._close()

    def record(self, *events: DomainEvent) -> None:
        """Acumula eventos para despacharlos en `commit()`."""
        if self._dispatching:
            raise RuntimeError(
                "un manejador in_transaction no puede registrar eventos nuevos (evita cascadas)"
            )
        self._events.extend(events)

    async def commit(self) -> None:
        events = list(self._events)
        self._dispatching = True
        try:
            await self._bus.dispatch_in_transaction(events, self)
        finally:
            self._dispatching = False
        await self._commit()
        self._events.clear()
        await self._bus.dispatch_after_commit(events)

    async def rollback(self) -> None:
        self._events.clear()
        await self._rollback()

    async def _begin(self) -> None:  # noqa: B027 - opcional para las implementaciones
        """Prepara la unidad de trabajo (por ejemplo, abrir la sesión)."""

    async def _close(self) -> None:  # noqa: B027 - opcional para las implementaciones
        """Libera recursos al salir del bloque."""

    @abstractmethod
    async def _commit(self) -> None: ...

    @abstractmethod
    async def _rollback(self) -> None: ...
