"""T109: sección `banco_de_items` de «Mis datos» (FR-031 de 001; research R-14).

Lista los ítems y versiones en que la persona participó (autora, colaboradora, revisora o quien
retiró), sus eventos con los comentarios y motivos que ella escribió, y sus importaciones,
exportaciones y cambios de la taxonomía. Nunca el contenido de los ítems ni datos de otras
personas.
"""

import json
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.content.application.bank_export import BankExport, ExportRequest
from saber_uli.content.application.review import Review
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.infrastructure.interchange.export_format import EXPORT_WRITERS
from saber_uli.identity.domain.roles import Role
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.content.imports import bank_file, importer, lc_item
from tests.integration.identity.staff import StaffFactory, accept_current_policy

NOW = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)
EXPORT = "/api/v1/me/data-export"


async def test_la_seccion_del_banco_solo_trae_lo_de_la_persona(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    app_engine: AsyncEngine,
) -> None:
    teacher = await staff(Role.TEACHER)
    admin = await staff(Role.ADMIN)
    other = await staff(Role.TEACHER)
    for person in (teacher, admin, other):
        await accept_current_policy(app_engine, person.id)

    service = importer(content_uow, NOW)
    mine = await service.preview(
        bank_file([lc_item(1), lc_item(2)]), "mi-banco-privado.json", teacher.id
    )
    assert mine.id is not None
    await service.confirm(
        mine.id, teacher.id, target_state=VersionState.IN_REVIEW, originality_declared=True
    )
    theirs = await service.preview(bank_file([lc_item(3)]), "de-otra.json", other.id)
    assert theirs.id is not None
    await service.confirm(
        theirs.id, other.id, target_state=VersionState.IN_REVIEW, originality_declared=True
    )
    review = Review(uow_factory=content_uow, clock=FixedClock(NOW))
    async with content_uow() as uow:
        first = await uow.items.get_by_code("LC-0001")
        second = await uow.items.get_by_code("LC-0002")
    assert first is not None and second is not None
    await review.approve(
        "LC-0001",
        admin.id,
        expected_revision=first.revision,
        confirms_alignment=True,
        confirms_originality=True,
    )
    await review.return_to_draft(
        "LC-0002", admin.id, expected_revision=second.revision, comment="Revisa la clave B."
    )
    await review.comment("LC-0002", teacher.id, "Ya corregí la clave.")
    exported = await BankExport(
        uow_factory=content_uow, clock=FixedClock(NOW), writers=EXPORT_WRITERS
    ).export(ExportRequest(format="json", module="LC"), teacher.id)
    _ = [chunk async for chunk in exported.chunks]

    teacher_data = (await api_client.get(EXPORT, headers=teacher.headers)).json()
    admin_data = (await api_client.get(EXPORT, headers=admin.headers)).json()

    section = teacher_data["sections"]["banco_de_items"]
    assert section["versiones"] == [
        {"item": "LC-0001", "version": 1, "estado": "published", "participacion": ["autor"]},
        {"item": "LC-0002", "version": 1, "estado": "draft", "participacion": ["autor"]},
    ]
    assert [(e["item"], e["tipo"]) for e in section["eventos"]] == [
        ("LC-0001", "imported"),
        ("LC-0002", "imported"),
        ("LC-0002", "commented"),
    ]
    assert section["eventos"][-1]["comentario"] == "Ya corregí la clave."
    assert [i["estado"] for i in section["importaciones"]] == ["confirmed"]
    assert section["importaciones"][0]["creados"] == 2
    assert [(e["formato"], e["items"]) for e in section["exportaciones"]] == [("json", 1)]
    assert section["cambios_taxonomia"] == []

    reviewer = admin_data["sections"]["banco_de_items"]
    assert [(v["item"], v["participacion"]) for v in reviewer["versiones"]] == [
        ("LC-0001", ["revisor"]),
        ("LC-0002", ["revisor"]),
    ]
    assert reviewer["eventos"][-1]["comentario"] == "Revisa la clave B."

    text = json.dumps(teacher_data, ensure_ascii=False)
    for foreign in ("LC-0003", "Revisa la clave B.", "mi-banco-privado", "de-otra"):
        assert foreign not in text
    for content in ("¿Qué sostiene el autor", "Opción A del ítem", "Un texto breve"):
        assert content not in text
