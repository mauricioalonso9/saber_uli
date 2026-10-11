"""T069: `purge_expired_imports` (research R-05; data-model §2.9).

Las importaciones pendientes vencidas quedan `expired` y sin contenido por aplicar; las
confirmadas y las que aún no vencen no cambian.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from saber_uli.content.domain.import_job import ImportStatus
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.infrastructure.tasks import purge_expired_imports
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.content.imports import bank_file, importer, lc_item

NOW = datetime(2026, 10, 9, 20, 0, tzinfo=UTC)
TEACHER = uuid4()


async def test_vence_las_pendientes_y_no_toca_las_demas(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    yesterday = importer(content_uow, NOW - timedelta(hours=25))
    expired = await yesterday.preview(bank_file([lc_item(1)]), "viejo.json", TEACHER)
    confirmed = await yesterday.preview(bank_file([lc_item(2)]), "otro.json", TEACHER)
    # Confirmada a tiempo (vencía una hora antes de NOW).
    await importer(content_uow, NOW - timedelta(hours=2)).confirm(
        confirmed.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
    )
    recent = await importer(content_uow, NOW - timedelta(hours=1)).preview(
        bank_file([lc_item(3)]), "nuevo.json", TEACHER
    )

    first = await purge_expired_imports(uow_factory=content_uow, clock=FixedClock(NOW))
    again = await purge_expired_imports(uow_factory=content_uow, clock=FixedClock(NOW))

    assert (first, again) == (1, 0)
    async with content_uow() as uow:
        gone = await uow.imports.get(expired.id)
        done = await uow.imports.get(confirmed.id)
        kept = await uow.imports.get(recent.id)
    assert gone is not None and gone.status is ImportStatus.EXPIRED and gone.payload is None
    assert done is not None and done.status is ImportStatus.CONFIRMED
    assert kept is not None and kept.status is ImportStatus.PENDING and kept.payload is not None
