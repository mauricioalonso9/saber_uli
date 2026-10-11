"""T066: vista previa de una importación (US4; FR-030 a FR-033, FR-037; research R-05).

Se valida todo el archivo y se guarda una importación pendiente con el resultado por fila y el
contenido listo para aplicar; no se guarda ningún ítem. Vence a las 24 horas.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from saber_uli.content.application.authoring import Authoring
from saber_uli.content.application.bundle import (
    BatchTooLargeError,
    UnreadableFileError,
    UnsupportedFileFormatError,
)
from saber_uli.content.application.contexts import Contexts
from saber_uli.content.domain.context import ContextContent, ContextKind
from saber_uli.content.domain.import_job import ImportAction, ImportStatus
from saber_uli.content.domain.item_version import Difficulty, ItemContent, ItemKind, Option
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.content.imports import bank_file, importer, lc_item

NOW = datetime(2026, 10, 9, 20, 0, tzinfo=UTC)
TEACHER = uuid4()


async def test_validos_e_invalidos_con_su_motivo(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    invalid = [
        lc_item(21, opciones=lc_item(21)["opciones"][:3]),
        lc_item(22, afirmacion="LC-A9"),
        lc_item(
            23,
            opciones=[
                {**option, "retroalimentacion": "" if option["clave"] == "B" else "Ok."}
                for option in lc_item(23)["opciones"]
            ],
        ),
    ]
    content = bank_file([lc_item(n) for n in range(1, 21)] + invalid)

    job = await importer(content_uow, NOW).preview(content, "banco.json", TEACHER)

    items = [row for row in job.rows if row.entity == "item"]
    assert job.counts() == {"create": 21, "update": 0, "unchanged": 0, "error": 3}
    assert sum(row.action is ImportAction.CREATE for row in items) == 20
    errors = {row.code: row.errors for row in items if row.action is ImportAction.ERROR}
    assert [(i.field, i.rule) for i in errors["LC-0021"]] == [
        ("options", ValidationRule.OPTION_COUNT)
    ]
    assert errors["LC-0022"][0].rule is ValidationRule.TAXONOMY_UNKNOWN
    assert errors["LC-0022"][0].field == "taxonomy.assertion_id"
    assert [(i.field, i.rule) for i in errors["LC-0023"]] == [
        ("options[B].feedback", ValidationRule.OPTION_FEEDBACK_REQUIRED)
    ]
    assert all(issue.message for issues in errors.values() for issue in issues)


async def test_duplicados_del_banco_y_del_archivo(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    clock = FixedClock(NOW)
    await Contexts(uow_factory=content_uow, clock=clock).create(
        code="LC-CTX-701",
        module="LC",
        content=ContextContent(
            kind=ContextKind.TEXT,
            title="Desconectar para aprender",
            body_md="Un texto breve de opinión.",
            text_type_node_id=lc_taxonomy.text_type.id,
        ),
        actor=TEACHER,
    )
    source = lc_item(1)
    await Authoring(uow_factory=content_uow, clock=clock).create(
        code="LC-0500",
        module="LC",
        kind=ItemKind.SELECTION,
        content=ItemContent(
            difficulty=Difficulty.MEDIUM,
            stem_md=source["enunciado"],
            explanation_md="Otra explicación.",
            taxonomy=TaxonomyTags(
                competence_id=lc_taxonomy.competence.id,
                assertion_id=lc_taxonomy.assertion.id,
                evidence_id=lc_taxonomy.evidence.id,
            ),
            options=tuple(
                Option(key=o["clave"], text=o["texto"], correct=o["correcta"], feedback="x")
                for o in source["opciones"]
            ),
            context_code="LC-CTX-701",
        ),
        actor=TEACHER,
    )
    copy_in_file = {**lc_item(2), "id": "LC-0003"}

    job = await importer(content_uow, NOW).preview(
        bank_file([lc_item(1), lc_item(2), copy_in_file], contexts=[]), "banco.json", TEACHER
    )

    rules = {row.code: [i.rule for i in row.errors] for row in job.rows}
    assert rules["LC-0001"] == [ValidationRule.DUPLICATE_ITEM]
    assert rules["LC-0002"] == []
    assert rules["LC-0003"] == [ValidationRule.DUPLICATE_IN_FILE]


async def test_contexto_inexistente(content_uow: UowFactory, lc_taxonomy: LcTaxonomy) -> None:
    job = await importer(content_uow, NOW).preview(
        bank_file([lc_item(1, contexto_id="LC-CTX-999")]), "banco.json", TEACHER
    )

    [row] = [row for row in job.rows if row.code == "LC-0001"]
    assert [(i.field, i.rule) for i in row.errors] == [
        ("context_code", ValidationRule.CONTEXT_UNKNOWN)
    ]


async def test_origen_ia_entra_en_revision(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    job = await importer(content_uow, NOW).preview(
        bank_file([lc_item(1, origen="ia"), lc_item(2)]), "banco.json", TEACHER
    )

    states = {row.code: row.target_state for row in job.rows if row.entity == "item"}
    assert states == {"LC-0001": "in_review", "LC-0002": None}


async def test_mas_de_1000_items(content_uow: UowFactory, lc_taxonomy: LcTaxonomy) -> None:
    with pytest.raises(BatchTooLargeError):
        await importer(content_uow, NOW).preview(
            bank_file([lc_item(n) for n in range(1, 1002)]), "banco.json", TEACHER
        )


@pytest.mark.parametrize(
    ("content", "name", "error"),
    [
        (b"{no es json", "banco.json", UnreadableFileError),
        (b'{"esquema_version": "2.0"}', "banco.json", UnreadableFileError),
        (b"a,b,c", "banco.csv", UnsupportedFileFormatError),
        (b'{"esquema_version": "1.0"}', "banco.xlsx", UnsupportedFileFormatError),
    ],
)
async def test_archivos_ilegibles_o_de_otro_formato(
    content_uow: UowFactory, content: bytes, name: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        await importer(content_uow, NOW).preview(content, name, TEACHER)


async def test_no_guarda_items_y_queda_pendiente_24_horas(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    job = await importer(content_uow, NOW).preview(
        bank_file([lc_item(1)]), "C:\\Users\\docente\\banco.json", TEACHER
    )

    async with content_uow() as uow:
        stored = await uow.imports.get(job.id)
        assert await uow.items.get_by_code("LC-0001") is None
        assert await uow.contexts.get_by_code("LC-CTX-701") is None
    assert stored is not None
    assert stored.status is ImportStatus.PENDING
    assert stored.expires_at == NOW + timedelta(hours=24)
    assert stored.source_name == "banco.json"
    assert stored.format == "json"
    assert stored.payload is not None
    assert stored.created_by == TEACHER
