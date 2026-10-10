"""T079: actualización de ítems en lote con versiones (US5; FR-015, FR-016, FR-035, SC-002).

Reimportar un código existente sigue las reglas de versiones: lo publicado o retirado recibe una
versión nueva y lo abierto se actualiza en su lugar. Un contenido idéntico no crea nada.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from saber_uli.content.application.review import Review
from saber_uli.content.domain.events import HistoryEventType
from saber_uli.content.domain.import_job import ImportAction
from saber_uli.content.domain.item_version import VersionState
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.content.imports import bank_file, importer, lc_item

NOW = datetime(2026, 10, 9, 20, 0, tzinfo=UTC)
TEACHER = uuid4()
OTHER_TEACHER = uuid4()
ADMIN = uuid4()


async def _import(
    uow: UowFactory,
    items: list[dict[str, Any]],
    actor: UUID = TEACHER,
    *,
    at: datetime = NOW,
    state: VersionState = VersionState.IN_REVIEW,
) -> Any:
    service = importer(uow, at)
    job = await service.preview(bank_file(items), "banco.json", actor)
    assert job.id is not None
    return await service.confirm(job.id, actor, target_state=state, originality_declared=True)


async def _publish(uow: UowFactory, code: str, at: datetime = NOW) -> None:
    async with uow() as unit:
        item = await unit.items.get_by_code(code)
    assert item is not None
    await Review(uow_factory=uow, clock=FixedClock(at)).approve(
        code,
        ADMIN,
        expected_revision=item.revision,
        confirms_alignment=True,
        confirms_originality=True,
    )


async def _versions(uow: UowFactory, code: str) -> list[tuple[int, VersionState]]:
    async with uow() as unit:
        return [(v.number, v.state) for v in await unit.items.versions(code)]


async def test_un_contenido_cambiado_da_actualizacion_con_diferencias(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await _import(content_uow, [lc_item(1), lc_item(2)])

    job = await importer(content_uow, NOW).preview(
        bank_file([lc_item(1, enunciado="¿Qué propone el autor?", dificultad="alta"), lc_item(2)]),
        "banco.json",
        OTHER_TEACHER,
    )

    rows = {row.code: row for row in job.rows if row.entity == "item"}
    assert rows["LC-0001"].action is ImportAction.UPDATE
    changes = {change.field: (change.before, change.after) for change in rows["LC-0001"].changes}
    assert changes == {
        "difficulty": ("medium", "high"),
        "stem_md": ("¿Qué sostiene el autor en el párrafo 1?", "¿Qué propone el autor?"),
    }
    assert rows["LC-0002"].action is ImportAction.UNCHANGED
    assert rows["LC-0002"].changes == []
    assert job.counts()["update"] == 1
    assert job.counts()["unchanged"] == 2  # LC-0002 y el contexto


async def test_lo_publicado_recibe_una_version_nueva_y_sigue_vigente(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await _import(content_uow, [lc_item(1)])
    await _publish(content_uow, "LC-0001")

    done = await _import(
        content_uow,
        [lc_item(1, enunciado="Versión corregida")],
        OTHER_TEACHER,
        at=NOW + timedelta(hours=1),
        state=VersionState.DRAFT,
    )

    assert done.result == {"created": 0, "versioned": 1, "skipped": []}
    assert await _versions(content_uow, "LC-0001") == [
        (1, VersionState.PUBLISHED),
        (2, VersionState.DRAFT),
    ]
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001")
        history = await uow.items.history("LC-0001")
    assert item is not None and item.published is not None and item.open is not None
    assert item.published.content.stem_md == "¿Qué sostiene el autor en el párrafo 1?"
    assert item.open.content.stem_md == "Versión corregida"
    assert item.open.contributor_ids == frozenset({OTHER_TEACHER})
    assert item.open.author_id == OTHER_TEACHER
    assert history[-1].type is HistoryEventType.IMPORTED
    assert history[-1].version_number == 2
    assert history[-1].details["import_id"] == str(done.id)


async def test_lo_abierto_se_actualiza_en_su_lugar(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await _import(content_uow, [lc_item(1)], state=VersionState.DRAFT)
    await _import(content_uow, [lc_item(2)], state=VersionState.IN_REVIEW)

    done = await _import(
        content_uow,
        [lc_item(1, enunciado="Borrador corregido"), lc_item(2, enunciado="Revisión corregida")],
        OTHER_TEACHER,
        at=NOW + timedelta(hours=1),
        state=VersionState.IN_REVIEW,
    )

    assert done.result == {"created": 0, "versioned": 2, "skipped": []}
    assert await _versions(content_uow, "LC-0001") == [(1, VersionState.IN_REVIEW)]
    assert await _versions(content_uow, "LC-0002") == [(1, VersionState.IN_REVIEW)]
    async with content_uow() as uow:
        first = await uow.items.get_by_code("LC-0001")
        second = await uow.items.get_by_code("LC-0002")
    assert first is not None and first.open is not None
    assert first.open.content.stem_md == "Borrador corregido"
    assert first.open.contributor_ids == frozenset({TEACHER, OTHER_TEACHER})
    assert second is not None and second.open is not None
    assert second.open.content.stem_md == "Revisión corregida"
    assert second.open.contributor_ids == frozenset({TEACHER, OTHER_TEACHER})
    # Quien importó la versión no puede aprobarla (FR-012).
    assert not second.can_approve(OTHER_TEACHER)


async def test_en_revision_vuelve_a_borrador_si_se_elige_borrador(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await _import(content_uow, [lc_item(1)], state=VersionState.IN_REVIEW)

    await _import(
        content_uow,
        [lc_item(1, enunciado="Corregido")],
        OTHER_TEACHER,
        at=NOW + timedelta(hours=1),
        state=VersionState.DRAFT,
    )

    assert await _versions(content_uow, "LC-0001") == [(1, VersionState.DRAFT)]


async def test_un_item_retirado_recibe_una_version_nueva(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await _import(content_uow, [lc_item(1)])
    await _publish(content_uow, "LC-0001")
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001")
    assert item is not None
    await Review(uow_factory=content_uow, clock=FixedClock(NOW)).retire(
        "LC-0001", ADMIN, expected_revision=item.revision, reason="Desactualizado"
    )

    later = NOW + timedelta(hours=1)
    preview = await importer(content_uow, later).preview(
        bank_file([lc_item(1)]), "banco.json", OTHER_TEACHER
    )
    [row] = [row for row in preview.rows if row.code == "LC-0001"]
    # Mismo contenido, pero retirado: reimportarlo lo devuelve al flujo con una versión nueva.
    assert row.action is ImportAction.UPDATE
    assert preview.id is not None
    done = await importer(content_uow, later).confirm(
        preview.id, OTHER_TEACHER, target_state=VersionState.DRAFT, originality_declared=True
    )

    assert done.result == {"created": 0, "versioned": 1, "skipped": []}
    assert await _versions(content_uow, "LC-0001") == [
        (1, VersionState.RETIRED),
        (2, VersionState.DRAFT),
    ]
    async with content_uow() as uow:
        history = await uow.items.history("LC-0001")
    types = [event.type for event in history]
    assert HistoryEventType.RETIRED in types
    assert types.index(HistoryEventType.RETIRED) < len(types) - 1
    assert history[-1].type is HistoryEventType.IMPORTED


async def test_repetir_la_importacion_no_crea_versiones(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await _import(content_uow, [lc_item(1), lc_item(2), lc_item(3)])
    await _publish(content_uow, "LC-0001")
    changed = [lc_item(1, enunciado="Cambio uno"), lc_item(2, enunciado="Cambio dos"), lc_item(3)]
    later = NOW + timedelta(hours=1)
    await _import(content_uow, changed, OTHER_TEACHER, at=later)
    async with content_uow() as uow:
        before = {code: await uow.items.get_by_code(code) for code in ("LC-0001", "LC-0002")}

    again = await importer(content_uow, later).preview(
        bank_file(changed), "banco.json", OTHER_TEACHER
    )

    assert {row.action for row in again.rows} == {ImportAction.UNCHANGED}
    assert again.counts()["update"] == 0 and again.counts()["create"] == 0
    assert await _versions(content_uow, "LC-0001") == [
        (1, VersionState.PUBLISHED),
        (2, VersionState.IN_REVIEW),
    ]
    async with content_uow() as uow:
        for code, item in before.items():
            stored = await uow.items.get_by_code(code)
            assert item is not None and stored is not None
            assert stored.revision == item.revision
