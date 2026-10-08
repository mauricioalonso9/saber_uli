"""Días hábiles en Colombia (research R-25; FR-032, SC-006).

No cuentan sábados, domingos ni festivos nacionales. Los festivos vienen de `holidays`, que
incluye los trasladados al lunes por la Ley Emiliani y los que dependen de la Pascua.

La fecha límite de una solicitud de supresión es la fecha de la solicitud en Bogotá más 15 días
hábiles; el día de la solicitud no cuenta.
"""

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import holidays

DELETION_BUSINESS_DAYS = 15
BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")  # sin horario de verano


@lru_cache(maxsize=32)
def _holidays(year: int) -> frozenset[date]:
    return frozenset(holidays.country_holidays("CO", years=year))


def is_business_day(day: date) -> bool:
    return day.weekday() < 5 and day not in _holidays(day.year)


def add_business_days(start: date, days: int) -> date:
    """`start` más `days` días hábiles (el propio `start` no cuenta)."""
    if days < 0:
        raise ValueError("los días hábiles no pueden ser negativos")
    current, remaining = start, days
    while remaining:
        current += timedelta(days=1)
        if is_business_day(current):
            remaining -= 1
    return current


def deletion_due_date(requested_at: datetime) -> date:
    if requested_at.tzinfo is None:
        raise ValueError("la hora de la solicitud debe tener zona horaria")
    return add_business_days(requested_at.astimezone(BOGOTA).date(), DELETION_BUSINESS_DAYS)
