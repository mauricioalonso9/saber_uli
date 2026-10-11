"""Estadísticas de una versión publicada (FR-041 a FR-044; research R-13).

Función pura sobre las **primeras** respuestas de cada estudiante a la versión. Cada respuesta
trae si acertó, la opción elegida y su puntaje del resto (proporción de acierto del estudiante en
otros ítems del mismo módulo); ninguna trae quién respondió (FR-044).

La discriminación es la correlación punto-biserial corregida: la de Pearson entre el acierto en
el ítem (0 o 1) y el puntaje del resto, que ya excluye este ítem. Con menos de 30 respuestas no
hay cifras ni señales (FR-042).
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

MIN_RESPONSES = 30
TOO_EASY_ABOVE = 0.9
TOO_HARD_BELOW = 0.2


class ProblemSignal(StrEnum):
    TOO_EASY = "too_easy"
    TOO_HARD = "too_hard"
    NEGATIVE_DISCRIMINATION = "negative_discrimination"
    DISTRACTOR_BEATS_KEY = "distractor_beats_key"


@dataclass(frozen=True)
class FirstResponse:
    correct: bool
    option: str | None  # None: no eligió ninguna (cuenta como error)
    rest_score: float


@dataclass(frozen=True)
class VersionStats:
    first_responses: int
    sufficient_data: bool
    correct_rate: float | None = None
    option_rates: dict[str, float] | None = None
    discrimination: float | None = None
    signals: tuple[ProblemSignal, ...] = ()


def version_statistics(
    responses: Sequence[FirstResponse], *, options: Sequence[str], key: str
) -> VersionStats:
    total = len(responses)
    if total < MIN_RESPONSES:
        return VersionStats(first_responses=total, sufficient_data=False)
    chosen = Counter(r.option for r in responses if r.option is not None)
    correct_rate = sum(r.correct for r in responses) / total
    option_rates = {option: chosen[option] / total for option in options}
    discrimination = _correlation(
        [1.0 if r.correct else 0.0 for r in responses], [r.rest_score for r in responses]
    )
    signals: list[ProblemSignal] = []
    if correct_rate > TOO_EASY_ABOVE:
        signals.append(ProblemSignal.TOO_EASY)
    if correct_rate < TOO_HARD_BELOW:
        signals.append(ProblemSignal.TOO_HARD)
    if discrimination is not None and discrimination < 0:
        signals.append(ProblemSignal.NEGATIVE_DISCRIMINATION)
    key_rate = option_rates.get(key, 0.0)
    if any(rate > key_rate for option, rate in option_rates.items() if option != key):
        signals.append(ProblemSignal.DISTRACTOR_BEATS_KEY)
    return VersionStats(
        first_responses=total,
        sufficient_data=True,
        correct_rate=correct_rate,
        option_rates=option_rates,
        discrimination=discrimination,
        signals=tuple(signals),
    )


def _correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson; `None` si alguna de las dos variables no varía."""
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    syy = sum((y - mean_y) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    return max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))
