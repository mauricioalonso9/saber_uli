"""T096: estadísticas de una versión (US8; FR-041 a FR-043; research R-13).

Datos sintéticos de resultado conocido. La discriminación es la punto-biserial corregida: la
correlación entre el acierto en el ítem y el puntaje del resto (el acierto del estudiante en los
otros ítems del módulo), comparada con `statistics.correlation` como referencia.
"""

import statistics

import pytest

from saber_uli.content.domain.statistics import (
    MIN_RESPONSES,
    FirstResponse,
    ProblemSignal,
    version_statistics,
)

OPTIONS = ("A", "B", "C", "D")


def responses(
    chosen: list[str], rest: list[float] | None = None, key: str = "A"
) -> list[FirstResponse]:
    scores = rest if rest is not None else [0.5] * len(chosen)
    return [
        FirstResponse(correct=option == key, option=option, rest_score=score)
        for option, score in zip(chosen, scores, strict=True)
    ]


def test_acierto_y_porcentaje_por_opcion() -> None:
    chosen = ["A"] * 24 + ["B"] * 8 + ["C"] * 6 + ["D"] * 2  # 40 respuestas
    rest = [0.2 + 0.015 * i for i in range(40)]

    result = version_statistics(responses(chosen, rest), options=OPTIONS, key="A")

    assert result.first_responses == 40
    assert result.sufficient_data is True
    assert result.correct_rate == pytest.approx(0.6)
    assert result.option_rates == pytest.approx({"A": 0.6, "B": 0.2, "C": 0.15, "D": 0.05})


def test_la_discriminacion_es_la_punto_biserial_corregida() -> None:
    chosen = ["A", "B", "A", "C", "A", "A", "D", "B", "A", "A"] * 4
    rest = [0.9, 0.3, 0.7, 0.2, 0.8, 0.6, 0.4, 0.5, 0.95, 0.65] * 4
    data = responses(chosen, rest)

    result = version_statistics(data, options=OPTIONS, key="A")

    reference = statistics.correlation([float(r.correct) for r in data], rest)
    assert result.discrimination == pytest.approx(reference, abs=1e-6)
    assert result.discrimination is not None and result.discrimination > 0
    assert ProblemSignal.NEGATIVE_DISCRIMINATION not in result.signals


def test_menos_de_30_respuestas_no_dan_cifras() -> None:
    result = version_statistics(responses(["A"] * (MIN_RESPONSES - 1)), options=OPTIONS, key="A")

    assert MIN_RESPONSES == 30
    assert result.first_responses == 29
    assert result.sufficient_data is False
    assert result.correct_rate is None
    assert result.option_rates is None
    assert result.discrimination is None
    assert result.signals == ()


def test_sin_respuestas() -> None:
    result = version_statistics([], options=OPTIONS, key="A")

    assert (result.first_responses, result.sufficient_data, result.signals) == (0, False, ())


def test_muy_facil_y_muy_dificil() -> None:
    easy = ["A"] * 28 + ["B"] * 2  # 0,933
    hard = ["A"] * 5 + ["B"] * 9 + ["C"] * 8 + ["D"] * 8  # 0,167
    limit = ["A"] * 27 + ["B"] * 3  # 0,9 exacto: no es "> 0,9"

    assert (
        ProblemSignal.TOO_EASY
        in version_statistics(responses(easy), options=OPTIONS, key="A").signals
    )
    assert (
        ProblemSignal.TOO_HARD
        in version_statistics(responses(hard), options=OPTIONS, key="A").signals
    )
    assert version_statistics(responses(limit), options=OPTIONS, key="A").signals == ()


def test_discriminacion_negativa_y_distractor_que_supera_a_la_clave() -> None:
    # Aciertan los de menor puntaje del resto; la B se elige más que la clave A.
    chosen = ["A"] * 12 + ["B"] * 15 + ["C"] * 3
    rest = [0.1] * 12 + [0.9] * 15 + [0.5] * 3

    result = version_statistics(responses(chosen, rest), options=OPTIONS, key="A")

    assert result.discrimination is not None and result.discrimination < 0
    assert set(result.signals) == {
        ProblemSignal.NEGATIVE_DISCRIMINATION,
        ProblemSignal.DISTRACTOR_BEATS_KEY,
    }


def test_varianza_cero_da_discriminacion_nula() -> None:
    same_rest = version_statistics(
        responses(["A"] * 20 + ["B"] * 20, [0.5] * 40), options=OPTIONS, key="A"
    )
    all_correct = version_statistics(
        responses(["A"] * 40, [i / 40 for i in range(40)]), options=OPTIONS, key="A"
    )

    assert same_rest.discrimination is None
    assert all_correct.discrimination is None
    assert ProblemSignal.NEGATIVE_DISCRIMINATION not in same_rest.signals


def test_una_respuesta_sin_opcion_cuenta_como_error() -> None:
    data = [*responses(["A"] * 30), FirstResponse(correct=False, option=None, rest_score=0.5)]

    result = version_statistics(data, options=OPTIONS, key="A")

    assert result.first_responses == 31
    assert result.correct_rate == pytest.approx(30 / 31)
    assert result.option_rates is not None
    assert sum(result.option_rates.values()) == pytest.approx(30 / 31)
