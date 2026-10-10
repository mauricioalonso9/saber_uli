"""Estadísticas de un ítem por versión (contrato: `getItemStatistics`; FR-041 a FR-044)."""

from collections.abc import Callable

from saber_uli.content.application.ports import StoredVersionStats
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.errors import ItemNotFoundError


class ItemStatisticsQuery:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, code: str) -> list[StoredVersionStats]:
        """Las versiones publicadas o retiradas, de la más reciente a la primera; una sin
        estadísticas calculadas aparece con 0 respuestas."""
        async with self._uow_factory() as uow:
            versions = await uow.items.statistics(code)
        if versions is None:
            raise ItemNotFoundError("El ítem no existe.")
        return versions
