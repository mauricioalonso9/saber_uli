"""Conservación de datos (research R-25; FR-034a, FR-034b, FR-034c).

Todo se calcula a partir de fechas, sin estados intermedios:

- Invitado: el acceso termina en mínimo(revocado_en, vence_en); aviso a los 60 días de ese fin
  y supresión a los 90 (la misma ventana en la que aún se puede renovar).
- Institucional: aviso a los 335 días del último ingreso y supresión a los 365.

Ingresar o renovar el acceso mueve las fechas y cancela el proceso. `retention_notice_sent_at`
evita repetir el aviso del ciclo vigente. La supresión no depende de que el aviso haya llegado
(FR-034c).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from saber_uli.identity.domain.business_days import BOGOTA

GUEST_NOTICE_AFTER = timedelta(days=60)
GUEST_ERASE_AFTER = timedelta(days=90)
INSTITUTIONAL_NOTICE_AFTER = timedelta(days=335)
INSTITUTIONAL_ERASE_AFTER = timedelta(days=365)


class RetentionAction(StrEnum):
    NONE = "none"
    SEND_NOTICE = "send_notice"
    ERASE = "erase"


@dataclass(frozen=True)
class RetentionSchedule:
    notice_at: datetime
    erase_at: datetime

    @property
    def erase_on(self) -> date:
        """Fecha de la supresión en Bogotá, para el aviso y las vistas."""
        return self.erase_at.astimezone(BOGOTA).date()


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("las fechas de conservación deben tener zona horaria")
    return moment


def guest_access_end(
    *, access_expires_at: datetime, revoked_at: datetime | None, now: datetime
) -> datetime | None:
    """Fin del acceso del invitado, o `None` si sigue vigente."""
    end = min(_aware(access_expires_at), _aware(revoked_at) if revoked_at else access_expires_at)
    return end if end <= _aware(now) else None


def guest_schedule(access_ended_at: datetime) -> RetentionSchedule:
    end = _aware(access_ended_at)
    return RetentionSchedule(notice_at=end + GUEST_NOTICE_AFTER, erase_at=end + GUEST_ERASE_AFTER)


def institutional_schedule(last_login_at: datetime) -> RetentionSchedule:
    login = _aware(last_login_at)
    return RetentionSchedule(
        notice_at=login + INSTITUTIONAL_NOTICE_AFTER, erase_at=login + INSTITUTIONAL_ERASE_AFTER
    )


def decide(
    schedule: RetentionSchedule, *, now: datetime, notice_sent_at: datetime | None
) -> RetentionAction:
    now = _aware(now)
    if now >= schedule.erase_at:
        return RetentionAction.ERASE
    # Un aviso anterior a la fecha de aviso vigente es de un ciclo que ya terminó.
    already_notified = notice_sent_at is not None and notice_sent_at >= schedule.notice_at
    if now >= schedule.notice_at and not already_notified:
        return RetentionAction.SEND_NOTICE
    return RetentionAction.NONE
