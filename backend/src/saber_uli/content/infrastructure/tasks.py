"""Tareas periódicas de `content` que ejecuta el worker.

`purge_expired_imports` (cada hora, idempotente; research R-05): las importaciones pendientes que
pasaron sus 24 horas quedan `expired` y pierden el contenido por aplicar (`payload`). El
resultado por fila se conserva como registro.

`refresh_item_statistics` (diaria, 03:00; research R-13): recalcula `item_version_stats`.
"""

from collections.abc import Callable

import structlog

from saber_uli.content.application.ports import ResponseStatisticsSource
from saber_uli.content.application.statistics_refresh import StatisticsRefresh
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.shared.domain.clock import Clock

_log = structlog.get_logger(__name__)


async def purge_expired_imports(
    *, uow_factory: Callable[[], ContentUnitOfWork], clock: Clock
) -> int:
    async with uow_factory() as uow:
        expired = await uow.imports.expire_pending(clock.now())
        await uow.commit()
    _log.info("imports_expired", count=expired)
    return expired


async def refresh_item_statistics(
    *,
    uow_factory: Callable[[], ContentUnitOfWork],
    source: ResponseStatisticsSource,
    clock: Clock,
) -> int:
    versions = await StatisticsRefresh(uow_factory=uow_factory, source=source, clock=clock).run()
    _log.info("item_statistics_refreshed", versions=versions)
    return versions
