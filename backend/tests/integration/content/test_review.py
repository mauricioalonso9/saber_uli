"""T041: revisión y publicación (US2; FR-010 a FR-015, FR-018; data-model §4 y §5).

Aprobar exige las dos confirmaciones y deja la historia; la publicada anterior pasa a retirada
(`superseded`). Nadie aprueba lo que creó o modificó. Devolver exige comentario y rechazar o
retirar, motivo. Cada acción compara la revisión esperada (R-09) y la sube.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from saber_uli.content.application.review import Review
from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.errors import (
    EditConflictError,
    InvalidTransitionError,
    ItemNotFoundError,
    SelfApprovalError,
)
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    Option,
    VersionState,
)
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.domain.errors import RuleViolationError
from tests.integration.content.conftest import LcTaxonomy, UowFactory

NOW = datetime(2026, 10, 9, 15, 0, tzinfo=UTC)
TEACHER = uuid4()
ADMIN = uuid4()
OTHER_ADMIN = uuid4()


async def in_review(
    content_uow: UowFactory, tax: LcTaxonomy, *, code: str = "LC-0001", author: UUID | None = None
) -> Item:
    content = ItemContent(
        difficulty=Difficulty.LOW,
        stem_md="¿Qué indica la expresión?",
        explanation_md="Se apoya en el texto.",
        taxonomy=TaxonomyTags(
            competence_id=tax.competence.id,
            assertion_id=tax.assertion.id,
            evidence_id=tax.evidence.id,
        ),
        options=tuple(
            Option(key=k, text=f"Opción {k}", correct=k == "A", feedback=f"Porque {k}")
            for k in "ABCD"
        ),
    )
    item = Item.create(
        code=code,
        module_code="LC",
        kind=ItemKind.SELECTION,
        origin=Origin.AI if author is None else Origin.TEACHER,
        content=content,
        content_hash=b"h",
        fingerprint=code.encode(),
        context_version_id=None,
        actor=author,
        now=NOW,
        state=VersionState.IN_REVIEW,
    )
    async with content_uow() as uow:
        await uow.items.add(item)
        await uow.commit()
    return item


@pytest.fixture
def review(content_uow: UowFactory) -> Review:
    return Review(uow_factory=content_uow, clock=FixedClock(NOW))


async def types(content_uow: UowFactory, code: str = "LC-0001") -> list[str]:
    async with content_uow() as uow:
        return [event.type.value for event in await uow.items.history(code)]


async def test_aprobar_publica_y_deja_la_historia_con_las_confirmaciones(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    item = await review.approve(
        "LC-0001", ADMIN, expected_revision=0, confirms_alignment=True, confirms_originality=True
    )

    assert item.published is not None
    assert item.published.reviewed_by == ADMIN
    assert item.published.published_at == NOW
    assert item.revision == 1
    async with content_uow() as uow:
        history = await uow.items.history("LC-0001")
    approved = history[-1]
    assert approved.type.value == "approved"
    assert approved.actor_id == ADMIN
    assert approved.details == {"confirms_alignment": True, "confirms_originality": True}


async def test_aprobar_una_version_nueva_retira_la_anterior(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)
    await review.approve(
        "LC-0001", ADMIN, expected_revision=0, confirms_alignment=True, confirms_originality=True
    )
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001", for_update=True)
        assert item is not None and item.published is not None
        item.edit(replace(item.published.content, stem_md="v2"), b"h2", b"f2", None, TEACHER, NOW)
        item.submit(TEACHER, NOW)
        await uow.items.save(item)
        await uow.commit()

    item = await review.approve(
        "LC-0001", ADMIN, expected_revision=3, confirms_alignment=True, confirms_originality=True
    )

    assert item.published is not None and item.published.number == 2
    assert "superseded" in await types(content_uow)


@pytest.mark.parametrize("approver", ["author", "contributor"])
async def test_nadie_aprueba_lo_que_creo_o_modifico(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy, approver: str
) -> None:
    await in_review(content_uow, lc_taxonomy, author=ADMIN if approver == "author" else TEACHER)
    if approver == "contributor":
        async with content_uow() as uow:
            item = await uow.items.get_by_code("LC-0001", for_update=True)
            assert item is not None and item.open is not None
            item.edit(item.open.content, b"h", b"f", None, ADMIN, NOW, keep_in_review=True)
            await uow.items.save(item)
            await uow.commit()
    revision = 0 if approver == "author" else 1

    with pytest.raises(SelfApprovalError):
        await review.approve(
            "LC-0001",
            ADMIN,
            expected_revision=revision,
            confirms_alignment=True,
            confirms_originality=True,
        )
    await review.approve(
        "LC-0001",
        OTHER_ADMIN,
        expected_revision=revision,
        confirms_alignment=True,
        confirms_originality=True,
    )


async def test_aprobar_sin_las_confirmaciones_no_publica(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    with pytest.raises(RuleViolationError):
        await review.approve(
            "LC-0001",
            ADMIN,
            expected_revision=0,
            confirms_alignment=True,
            confirms_originality=False,
        )
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001")
    assert item is not None and item.published is None


async def test_devolver_deja_borrador_con_el_comentario(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    item = await review.return_to_draft(
        "LC-0001", ADMIN, expected_revision=0, comment="Revisa la opción C."
    )

    assert item.open is not None and item.open.state is VersionState.DRAFT
    async with content_uow() as uow:
        history = await uow.items.history("LC-0001")
    assert (history[-1].type.value, history[-1].comment) == ("returned", "Revisa la opción C.")


async def test_rechazar_retira_sin_publicar(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    item = await review.reject(
        "LC-0001", ADMIN, expected_revision=0, reason="Reproduce una pregunta del ICFES."
    )

    assert item.open is None and item.published is None
    async with content_uow() as uow:
        history = await uow.items.history("LC-0001")
    assert (history[-1].type.value, history[-1].reason) == (
        "rejected",
        "Reproduce una pregunta del ICFES.",
    )


async def test_retirar_una_publicada(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)
    await review.approve(
        "LC-0001", ADMIN, expected_revision=0, confirms_alignment=True, confirms_originality=True
    )

    item = await review.retire("LC-0001", ADMIN, expected_revision=1, reason="Ambigua")

    assert item.published is None
    assert (await types(content_uow))[-1] == "retired"


async def test_transiciones_invalidas(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    with pytest.raises(InvalidTransitionError):
        await review.retire("LC-0001", ADMIN, expected_revision=0, reason="x")


async def test_la_revision_esperada_debe_coincidir(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    with pytest.raises(EditConflictError):
        await review.approve(
            "LC-0001",
            ADMIN,
            expected_revision=7,
            confirms_alignment=True,
            confirms_originality=True,
        )


async def test_un_item_que_no_existe(review: Review, lc_taxonomy: LcTaxonomy) -> None:
    with pytest.raises(ItemNotFoundError):
        await review.reject("LC-9999", ADMIN, expected_revision=0, reason="x")


async def test_comentar_no_cambia_estado_ni_revision(
    review: Review, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await in_review(content_uow, lc_taxonomy)

    event = await review.comment("LC-0001", TEACHER, "¿La opción B es ambigua?")

    assert event.id is not None
    assert (event.type.value, event.actor_id) == ("commented", TEACHER)
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001")
    assert item is not None and item.revision == 0
    assert item.open is not None and item.open.state is VersionState.IN_REVIEW
