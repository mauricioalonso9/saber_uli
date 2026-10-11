"""Recálculo nocturno de las estadísticas por versión (US8; FR-041 a FR-044; research R-13).

Pide a la fuente las primeras respuestas a cada versión publicada (vigente o retirada) de los
ítems de selección, calcula con `domain.statistics` y reemplaza la tabla completa, que es la que
filtra por señales de problema (SC-009). La fuente no entrega quién respondió.
"""

from collections.abc import Callable

from saber_uli.content.application.ports import ResponseStatisticsSource
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.statistics import version_statistics
from saber_uli.shared.domain.clock import Clock


class StatisticsRefresh:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], ContentUnitOfWork],
        source: ResponseStatisticsSource,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._source = source
        self._clock = clock

    async def run(self) -> int:
        """Recalcula y devuelve cuántas versiones quedaron en la tabla."""
        async with self._uow_factory() as uow:
            targets = await uow.items.statistics_targets()
        responses = await self._source.first_responses([t.version_id for t in targets])
        stats = [
            (
                target.version_id,
                version_statistics(
                    responses.get(target.version_id, ()), options=target.options, key=target.key
                ),
            )
            for target in targets
        ]
        async with self._uow_factory() as uow:
            await uow.items.replace_statistics(stats, self._clock.now())
            await uow.commit()
        return len(stats)
