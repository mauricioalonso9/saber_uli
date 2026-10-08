"""T152: días hábiles en Colombia (research R-25; FR-032, SC-006).

La fecha límite de una solicitud de supresión es la fecha de la solicitud en Bogotá más 15 días
hábiles: no cuentan sábados, domingos ni festivos de Colombia, incluidos los que la Ley Emiliani
traslada al lunes. El día de la solicitud no cuenta.
"""

from datetime import UTC, date, datetime

import pytest

from saber_uli.identity.domain.business_days import (
    DELETION_BUSINESS_DAYS,
    add_business_days,
    deletion_due_date,
    is_business_day,
)


def test_el_plazo_de_supresion_es_de_15_dias_habiles() -> None:
    assert DELETION_BUSINESS_DAYS == 15


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 7), True),  # miércoles
        (date(2026, 10, 10), False),  # sábado
        (date(2026, 10, 11), False),  # domingo
        (date(2026, 10, 12), False),  # Día de la Raza
        (date(2027, 1, 6), True),  # Reyes Magos se traslada al lunes 11 (Ley Emiliani)
        (date(2027, 1, 11), False),
        (date(2027, 3, 19), True),  # San José se traslada al lunes 22
        (date(2027, 3, 22), False),
        (date(2027, 3, 25), False),  # Jueves Santo
        (date(2027, 3, 26), False),  # Viernes Santo
        (date(2026, 12, 8), False),  # Inmaculada Concepción
        (date(2026, 12, 25), False),
        (date(2027, 1, 1), False),
    ],
)
def test_dia_habil(day: date, expected: bool) -> None:
    assert is_business_day(day) is expected


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        # Cruza el Día de la Raza (lunes 12 de octubre).
        (date(2026, 10, 5), date(2026, 10, 27)),
        # Empieza un sábado: cruza el 12 de octubre y Todos los Santos (lunes 2 de noviembre).
        (date(2026, 10, 10), date(2026, 11, 3)),
        # Semana Santa de 2027 y San José trasladado.
        (date(2027, 3, 15), date(2027, 4, 8)),
        # Fin de año: Navidad y Año Nuevo caen viernes; Reyes se traslada al 11 de enero.
        (date(2026, 12, 14), date(2027, 1, 6)),
    ],
)
def test_suma_15_dias_habiles(start: date, expected: date) -> None:
    assert add_business_days(start, 15) == expected


def test_sumar_cero_dias_devuelve_la_misma_fecha() -> None:
    assert add_business_days(date(2026, 10, 10), 0) == date(2026, 10, 10)


def test_no_admite_dias_negativos() -> None:
    with pytest.raises(ValueError, match="negativ"):
        add_business_days(date(2026, 10, 7), -1)


def test_la_fecha_limite_usa_la_fecha_de_bogota() -> None:
    # 2026-10-06 03:00 UTC es todavía el lunes 5 de octubre en Bogotá (UTC-5).
    assert deletion_due_date(datetime(2026, 10, 6, 3, 0, tzinfo=UTC)) == date(2026, 10, 27)
    # Al mediodía del 6 cuenta desde el martes.
    assert deletion_due_date(datetime(2026, 10, 6, 17, 0, tzinfo=UTC)) == date(2026, 10, 28)


def test_la_fecha_limite_exige_hora_con_zona() -> None:
    with pytest.raises(ValueError, match="zona"):
        deletion_due_date(datetime(2026, 10, 6, 12, 0))  # noqa: DTZ001
