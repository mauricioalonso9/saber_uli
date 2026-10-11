"""T067: confirmación de una importación (US4; FR-034 a FR-036; research R-05).

Entran todos los válidos o ninguno, en una transacción, con la declaración de originalidad. Un
ítem que otra persona creó o cambió después de la vista previa queda omitido.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.content.application.authoring import Authoring
from saber_uli.content.application.bank_import import (
    ImportNotPendingError,
    NothingToImportError,
)
from saber_uli.content.domain.events import HistoryEventType
from saber_uli.content.domain.import_job import ImportStatus
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    VersionState,
)
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.content.infrastructure.unit_of_work import SqlAlchemyContentUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.content.imports import bank_file, importer, lc_item

NOW = datetime(2026, 10, 9, 20, 0, tzinfo=UTC)
TEACHER = uuid4()


async def test_confirmar_crea_los_validos_con_la_declaracion(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy, app_engine: AsyncEngine
) -> None:
    service = importer(content_uow, NOW)
    job = await service.preview(
        bank_file([lc_item(1), lc_item(2, origen="ia"), lc_item(3, afirmacion="LC-A9")]),
        "banco.json",
        TEACHER,
    )

    done = await service.confirm(
        job.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
    )

    assert done.status is ImportStatus.CONFIRMED
    assert done.result == {"created": 2, "versioned": 0, "skipped": []}
    async with content_uow() as uow:
        first = await uow.items.get_by_code("LC-0001")
        second = await uow.items.get_by_code("LC-0002")
        assert await uow.items.get_by_code("LC-0003") is None
        assert await uow.contexts.get_by_code("LC-CTX-701") is not None
        history = await uow.items.history("LC-0001")
    assert first is not None and first.open is not None
    assert first.open.state is VersionState.DRAFT
    assert first.open.author_id == TEACHER
    assert second is not None and second.open is not None
    assert second.open.state is VersionState.IN_REVIEW  # origen IA
    assert history[-1].type is HistoryEventType.IMPORTED
    assert history[-1].details["import_id"] == str(job.id)
    async with app_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT status, originality_declared, target_state, confirmed_at, payload "
                    "FROM content.imports WHERE id = :id"
                ),
                {"id": job.id},
            )
        ).one()
    assert row.status == "confirmed"
    assert row.originality_declared is True
    assert row.target_state == "draft"
    assert row.confirmed_at == NOW
    assert row.payload is None


class _FailingItems:
    """Repositorio de ítems que falla al guardar el segundo ítem."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.added = 0

    async def add(self, item: Any) -> Any:
        self.added += 1
        if self.added == 2:
            raise RuntimeError("fallo inyectado")
        return await self._inner.add(item)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


async def test_un_fallo_a_mitad_no_deja_ninguno(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy, app_engine: AsyncEngine
) -> None:
    job = await importer(content_uow, NOW).preview(
        bank_file([lc_item(1), lc_item(2), lc_item(3)]), "banco.json", TEACHER
    )
    factory = create_session_factory(app_engine)

    class FailingUow(SqlAlchemyContentUnitOfWork):
        _failing: _FailingItems | None = None

        @property
        def items(self) -> Any:
            if self._failing is None:
                self._failing = _FailingItems(super().items)
            return self._failing

    with pytest.raises(RuntimeError):
        await importer(lambda: FailingUow(factory, EventBus()), NOW).confirm(
            job.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
        )

    async with content_uow() as uow:
        assert await uow.items.get_by_code("LC-0001") is None
        assert await uow.contexts.get_by_code("LC-CTX-701") is None
        stored = await uow.imports.get(job.id)
    assert stored is not None and stored.status is ImportStatus.PENDING


async def test_lo_creado_por_otra_persona_despues_se_omite(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    service = importer(content_uow, NOW)
    job = await service.preview(
        bank_file([lc_item(1, contexto_id=None), lc_item(2, contexto_id=None)], contexts=[]),
        "banco.json",
        TEACHER,
    )
    await Authoring(uow_factory=content_uow, clock=FixedClock(NOW)).create(
        code="LC-0002",
        module="LC",
        kind=ItemKind.SELECTION,
        content=ItemContent(
            difficulty=Difficulty.LOW,
            stem_md="Escrito por otra persona",
            explanation_md="",
            taxonomy=TaxonomyTags(),
        ),
        actor=uuid4(),
    )

    done = await service.confirm(
        job.id, TEACHER, target_state=VersionState.IN_REVIEW, originality_declared=True
    )

    assert done.result == {"created": 1, "versioned": 0, "skipped": ["LC-0002"]}
    [row] = [row for row in done.rows if row.code == "LC-0002"]
    assert [i.rule for i in row.errors] == [ValidationRule.CHANGED_SINCE_PREVIEW]
    async with content_uow() as uow:
        other = await uow.items.get_by_code("LC-0002")
    assert other is not None and other.open is not None
    assert other.open.content.stem_md == "Escrito por otra persona"


async def test_solo_se_confirma_una_vez_y_antes_de_vencer(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    service = importer(content_uow, NOW)
    first = await service.preview(bank_file([lc_item(1)]), "banco.json", TEACHER)
    second = await service.preview(bank_file([lc_item(2)]), "otro.json", TEACHER)
    await service.confirm(
        first.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
    )

    with pytest.raises(ImportNotPendingError):
        await service.confirm(
            first.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
        )
    later = importer(content_uow, NOW + timedelta(hours=24, seconds=1))
    with pytest.raises(ImportNotPendingError):
        await later.confirm(
            second.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
        )


async def test_sin_validos_no_hay_nada_que_importar(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    service = importer(content_uow, NOW)
    job = await service.preview(
        bank_file([lc_item(1, afirmacion="LC-A9")], contexts=[]), "banco.json", TEACHER
    )

    with pytest.raises(NothingToImportError):
        await service.confirm(
            job.id, TEACHER, target_state=VersionState.DRAFT, originality_declared=True
        )
