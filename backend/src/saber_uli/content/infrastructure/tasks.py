"""Tareas periódicas de `content` que ejecuta el worker.

`purge_expired_imports` (cada hora, idempotente; research R-05): las importaciones pendientes que
pasaron sus 24 horas quedan `expired` y pierden el contenido por aplicar (`payload`). El
resultado por fila se conserva como registro.
"""

from collections.abc import Callable

import structlog

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
