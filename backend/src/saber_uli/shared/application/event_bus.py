"""Bus de eventos en proceso con dos fases (research R-08, precisión 2026-10-06).

- `in_transaction`: corre dentro de `UnitOfWork.commit()`, antes del COMMIT y con la misma
  sesión. Es para escrituras que deben confirmarse junto con la acción (el outbox, T032). Si un
  manejador falla, la excepción se propaga y la unidad de trabajo se revierte.
- `after_commit`: corre justo después del COMMIT, para efectos fuera de la base de datos (por
  ejemplo, invalidar la caché de `auth_epoch`). Un fallo se registra y no deshace nada.

Lo que deba ocurrir de forma confiable (correos, supresiones) va al outbox, nunca a
`after_commit`. El bus no tiene estado global: se crea en la raíz de composición y se inyecta.
"""

from collections.abc import Awaitable, Callable, Iterable
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

import structlog

from saber_uli.shared.domain.events import DomainEvent

if TYPE_CHECKING:
    from saber_uli.shared.application.unit_of_work import UnitOfWork

Phase = Literal["in_transaction", "after_commit"]
PHASES: tuple[Phase, ...] = ("in_transaction", "after_commit")

E = TypeVar("E", bound=DomainEvent)

_log = structlog.get_logger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[Phase, list[tuple[type[DomainEvent], Callable[..., Awaitable[None]]]]]
        self._handlers = {phase: [] for phase in PHASES}

    @overload
    def subscribe(
        self,
        event_cls: type[E],
        handler: Callable[[E, "UnitOfWork"], Awaitable[None]],
        *,
        phase: Literal["in_transaction"],
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_cls: type[E],
        handler: Callable[[E], Awaitable[None]],
        *,
        phase: Literal["after_commit"],
    ) -> None: ...

    def subscribe(
        self, event_cls: type[E], handler: Callable[..., Awaitable[None]], *, phase: Phase
    ) -> None:
        """Suscribe `handler` a `event_cls` y sus subclases, en el orden de llamada."""
        if phase not in PHASES:
            raise ValueError(f"fase desconocida: {phase!r}; use una de {PHASES}")
        self._handlers[phase].append((event_cls, handler))

    def _matching(self, phase: Phase, event: DomainEvent) -> list[Callable[..., Awaitable[None]]]:
        return [h for cls, h in self._handlers[phase] if isinstance(event, cls)]

    async def dispatch_in_transaction(
        self, events: Iterable[DomainEvent], uow: "UnitOfWork"
    ) -> None:
        for event in events:
            for handler in self._matching("in_transaction", event):
                await handler(event, uow)

    async def dispatch_after_commit(self, events: Iterable[DomainEvent]) -> None:
        for event in events:
            for handler in self._matching("after_commit", event):
                try:
                    await handler(event)
                except Exception as error:
                    # Solo identificadores y la clase: el mensaje podría llevar datos personales.
                    _log.error(
                        "after_commit_handler_failed",
                        event_type=event.event_type,
                        event_id=str(event.event_id),
                        handler=_name(handler),
                        error_type=type(error).__name__,
                    )


def _name(handler: Any) -> str:
    return str(getattr(handler, "__qualname__", type(handler).__name__))
