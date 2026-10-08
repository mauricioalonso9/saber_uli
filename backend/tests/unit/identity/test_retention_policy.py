"""T153: política de conservación (research R-25; FR-034a, FR-034b, FR-034c).

- Invitado: el acceso termina en mínimo(revocado_en, vence_en); aviso a los 60 días y
  supresión a los 90.
- Institucional: aviso a los 335 días del último ingreso y supresión a los 365.
- Ingresar o renovar mueve las fechas y cancela el proceso sin estados intermedios.
- El aviso no se repite si ya se envió en este ciclo.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from saber_uli.identity.domain.retention import (
    RetentionAction,
    decide,
    guest_access_end,
    guest_schedule,
    institutional_schedule,
)

T0 = datetime(2026, 1, 10, 15, 0, tzinfo=UTC)


def days(n: float) -> timedelta:
    return timedelta(days=n)


# --- Invitados (FR-034a) ------------------------------------------------------------------------


def test_el_acceso_vigente_no_tiene_fin() -> None:
    assert guest_access_end(access_expires_at=T0 + days(10), revoked_at=None, now=T0) is None


def test_el_fin_del_acceso_es_el_vencimiento_si_no_hubo_revocacion() -> None:
    assert guest_access_end(access_expires_at=T0, revoked_at=None, now=T0 + days(1)) == T0


def test_el_fin_del_acceso_es_la_revocacion_si_fue_antes() -> None:
    revoked = T0 - days(20)
    end = guest_access_end(access_expires_at=T0, revoked_at=revoked, now=T0 + days(1))
    assert end == revoked


def test_una_revocacion_reciente_termina_el_acceso_aunque_no_haya_vencido() -> None:
    end = guest_access_end(access_expires_at=T0 + days(30), revoked_at=T0, now=T0 + days(1))
    assert end == T0


def test_calendario_del_invitado() -> None:
    schedule = guest_schedule(T0)
    assert schedule.notice_at == T0 + days(60)
    assert schedule.erase_at == T0 + days(90)
    assert schedule.erase_on == date(2026, 4, 10)


# --- Institucionales (FR-034b) ------------------------------------------------------------------


def test_calendario_del_institucional() -> None:
    schedule = institutional_schedule(T0)
    assert schedule.notice_at == T0 + days(335)
    assert schedule.erase_at == T0 + days(365)
    assert schedule.erase_on == date(2027, 1, 10)


def test_la_fecha_de_supresion_se_muestra_en_hora_de_bogota() -> None:
    # 02:00 UTC del 11 de enero es todavía el 10 de enero en Bogotá.
    late = datetime(2026, 1, 11, 2, 0, tzinfo=UTC)
    assert institutional_schedule(late).erase_on == date(2027, 1, 10)


# --- Decisión (FR-034c) -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (days(334), RetentionAction.NONE),
        (days(335), RetentionAction.SEND_NOTICE),
        (days(350), RetentionAction.SEND_NOTICE),
        (days(365), RetentionAction.ERASE),
        (days(400), RetentionAction.ERASE),
    ],
)
def test_decision_institucional_sin_aviso_previo(elapsed: timedelta, expected: str) -> None:
    schedule = institutional_schedule(T0)
    assert decide(schedule, now=T0 + elapsed, notice_sent_at=None) is expected


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (days(59), RetentionAction.NONE),
        (days(60), RetentionAction.SEND_NOTICE),
        (days(90), RetentionAction.ERASE),
    ],
)
def test_decision_del_invitado(elapsed: timedelta, expected: str) -> None:
    schedule = guest_schedule(T0)
    assert decide(schedule, now=T0 + elapsed, notice_sent_at=None) is expected


def test_el_aviso_no_se_repite() -> None:
    schedule = institutional_schedule(T0)
    sent = T0 + days(335)
    assert decide(schedule, now=T0 + days(340), notice_sent_at=sent) is RetentionAction.NONE


def test_la_supresion_no_depende_de_que_el_aviso_se_haya_enviado() -> None:
    """Si el correo no llegó, la supresión sigue en la fecha prevista (FR-034c)."""
    schedule = guest_schedule(T0)
    assert decide(schedule, now=T0 + days(91), notice_sent_at=None) is RetentionAction.ERASE


def test_un_aviso_de_un_ciclo_anterior_no_cuenta() -> None:
    """Un aviso enviado antes de la fecha de aviso vigente es de un ciclo que ya terminó."""
    schedule = institutional_schedule(T0)
    stale = T0 - days(10)
    assert decide(schedule, now=T0 + days(336), notice_sent_at=stale) is (
        RetentionAction.SEND_NOTICE
    )


def test_ingresar_mueve_las_fechas_y_cancela_la_supresion() -> None:
    now = T0 + days(360)  # ya se avisó y faltan 5 días
    assert decide(institutional_schedule(T0), now=now, notice_sent_at=T0 + days(335)) is (
        RetentionAction.NONE
    )
    relogin = T0 + days(358)
    assert decide(institutional_schedule(relogin), now=T0 + days(366), notice_sent_at=None) is (
        RetentionAction.NONE
    )


def test_renovar_el_acceso_del_invitado_cancela_la_supresion() -> None:
    renewed_until = T0 + days(100)
    now = T0 + days(95)  # el acceso anterior terminó en T0; el nuevo sigue vigente
    assert guest_access_end(access_expires_at=renewed_until, revoked_at=None, now=now) is None


def test_las_horas_deben_tener_zona() -> None:
    with pytest.raises(ValueError, match="zona"):
        institutional_schedule(datetime(2026, 1, 10, 15, 0))  # noqa: DTZ001
