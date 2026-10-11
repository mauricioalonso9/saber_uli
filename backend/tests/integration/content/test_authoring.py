"""T049: creación y edición de ítems (US3; FR-015, FR-016, FR-024, FR-027, FR-032).

Crear deja un Borrador; un código repetido o un contenido duplicado se rechazan. Guardar sobre lo
publicado crea una versión nueva; sobre una versión En revisión, vuelve a Borrador salvo
`keep_in_review`. Enviar exige contenido sin problemas.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from saber_uli.content.application.authoring import Authoring
from saber_uli.content.application.review import Review
from saber_uli.content.domain.errors import (
    CodeTakenError,
    ContentValidationError,
    DuplicateItemError,
    EditConflictError,
)
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    Option,
    VersionState,
)
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import LcTaxonomy, UowFactory

NOW = datetime(2026, 10, 9, 16, 0, tzinfo=UTC)
TEACHER = uuid4()
OTHER_TEACHER = uuid4()
ADMIN = uuid4()


def content(tax: LcTaxonomy, stem: str = "¿Qué indica la expresión?") -> ItemContent:
    return ItemContent(
        difficulty=Difficulty.MEDIUM,
        stem_md=stem,
        explanation_md="Se apoya en el segundo párrafo.",
        taxonomy=TaxonomyTags(
            competence_id=tax.competence.id,
            assertion_id=tax.assertion.id,
            evidence_id=tax.evidence.id,
        ),
        options=tuple(
            Option(key=k, text=f"Opción {k} de {stem[:10]}", correct=k == "A", feedback=f"Por {k}")
            for k in "ABCD"
        ),
    )


@pytest.fixture
def authoring(content_uow: UowFactory) -> Authoring:
    return Authoring(uow_factory=content_uow, clock=FixedClock(NOW))


@pytest.fixture
def review(content_uow: UowFactory) -> Review:
    return Review(uow_factory=content_uow, clock=FixedClock(NOW))


async def types(content_uow: UowFactory, code: str) -> list[str]:
    async with content_uow() as uow:
        return [event.type.value for event in await uow.items.history(code)]


async def test_crear_deja_un_borrador_con_el_autor(
    authoring: Authoring, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    item = await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )

    assert item.open is not None
    assert item.open.state is VersionState.DRAFT
    assert item.open.author_id == TEACHER
    assert item.open.contributor_ids == {TEACHER}
    assert await types(content_uow, "LC-0101") == ["created"]


async def test_codigo_repetido_y_contenido_duplicado(
    authoring: Authoring, lc_taxonomy: LcTaxonomy
) -> None:
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )

    with pytest.raises(CodeTakenError):
        await authoring.create(
            code="LC-0101",
            module="LC",
            kind=ItemKind.SELECTION,
            content=content(lc_taxonomy, "Otro enunciado"),
            actor=TEACHER,
        )
    # Mismo contenido con mayúsculas y puntuación distintas: duplicado (FR-032).
    copy = replace(content(lc_taxonomy), stem_md="¿QUÉ indica la expresión?!")
    with pytest.raises(DuplicateItemError):
        await authoring.create(
            code="LC-0102", module="LC", kind=ItemKind.SELECTION, content=copy, actor=TEACHER
        )


async def test_un_borrador_incompleto_se_guarda_pero_no_se_envia(
    authoring: Authoring, lc_taxonomy: LcTaxonomy
) -> None:
    incomplete = replace(content(lc_taxonomy), explanation_md="")
    await authoring.create(
        code="LC-0101", module="LC", kind=ItemKind.SELECTION, content=incomplete, actor=TEACHER
    )

    with pytest.raises(ContentValidationError) as error:
        await authoring.submit("LC-0101", TEACHER, expected_revision=0)

    assert ("explanation_md", ValidationRule.EXPLANATION_REQUIRED) in {
        (issue.field, issue.rule) for issue in error.value.issues
    }


async def test_guardar_y_enviar(
    authoring: Authoring, content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )
    saved = await authoring.save_draft(
        "LC-0101", content(lc_taxonomy, "Enunciado corregido"), OTHER_TEACHER, expected_revision=0
    )
    assert saved.open is not None and saved.open.contributor_ids == {TEACHER, OTHER_TEACHER}

    submitted = await authoring.submit("LC-0101", OTHER_TEACHER, expected_revision=1)

    assert submitted.open is not None
    assert submitted.open.state is VersionState.IN_REVIEW
    assert submitted.open.submitted_by == OTHER_TEACHER
    assert await types(content_uow, "LC-0101") == ["created", "edited", "submitted"]


async def test_con_otra_revision_es_un_conflicto(
    authoring: Authoring, lc_taxonomy: LcTaxonomy
) -> None:
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )

    with pytest.raises(EditConflictError):
        await authoring.save_draft(
            "LC-0101", content(lc_taxonomy, "x"), TEACHER, expected_revision=3
        )


async def test_editar_lo_publicado_crea_una_version_nueva(
    authoring: Authoring, review: Review, lc_taxonomy: LcTaxonomy
) -> None:
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )
    await authoring.submit("LC-0101", TEACHER, expected_revision=0)
    await review.approve(
        "LC-0101", ADMIN, expected_revision=1, confirms_alignment=True, confirms_originality=True
    )

    item = await authoring.save_draft(
        "LC-0101", content(lc_taxonomy, "Versión dos"), TEACHER, expected_revision=2
    )

    assert item.published is not None and item.published.number == 1
    assert item.published.content.stem_md == "¿Qué indica la expresión?"
    assert item.open is not None and item.open.number == 2
    assert item.open.state is VersionState.DRAFT


@pytest.mark.parametrize(
    ("keep", "expected"), [(False, VersionState.DRAFT), (True, VersionState.IN_REVIEW)]
)
async def test_editar_en_revision_vuelve_a_borrador_o_sigue(
    authoring: Authoring, lc_taxonomy: LcTaxonomy, keep: bool, expected: VersionState
) -> None:
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )
    await authoring.submit("LC-0101", TEACHER, expected_revision=0)

    item = await authoring.save_draft(
        "LC-0101",
        content(lc_taxonomy, "Ajuste en revisión"),
        OTHER_TEACHER,
        expected_revision=1,
        keep_in_review=keep,
    )

    assert item.open is not None and item.open.state is expected


async def test_el_borrador_de_un_docente_sin_el_rol_lo_continua_otro(
    authoring: Authoring, lc_taxonomy: LcTaxonomy
) -> None:
    # La pérdida del rol no toca el banco: el borrador sigue y otro docente lo envía.
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=content(lc_taxonomy),
        actor=TEACHER,
    )

    item = await authoring.submit("LC-0101", OTHER_TEACHER, expected_revision=0)

    assert item.open is not None and item.open.state is VersionState.IN_REVIEW
