"""Reloj inyectable: el dominio nunca consulta la hora del sistema directamente."""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Fecha y hora actual en UTC, con zona horaria."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("la fecha debe tener zona horaria")
    return value.astimezone(UTC)


class FixedClock:
    """Reloj para pruebas: devuelve siempre la misma hora hasta que se mueve."""

    def __init__(self, at: datetime) -> None:
        self._now = _as_utc(at)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def set(self, at: datetime) -> None:
        self._now = _as_utc(at)
