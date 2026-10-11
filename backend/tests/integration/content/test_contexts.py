"""T050: contextos compartidos (US3; FR-005, FR-007, FR-009, FR-020, FR-026).

Un contexto se guarda solo si es válido. Editarlo crea una versión nueva: los ítems publicados
que lo usan reciben una versión nueva En revisión y las versiones abiertas pasan a la nueva
versión del contexto.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from saber_uli.content.application.authoring import Authoring
from saber_uli.content.application.contexts import Contexts
from saber_uli.content.application.review import Review
from saber_uli.content.domain.context import ContextContent, ContextKind
from saber_uli.content.domain.errors import (
    CodeTakenError,
    ContentValidationError,
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

NOW = datetime(2026, 10, 9, 17, 0, tzinfo=UTC)
TEACHER = uuid4()
ADMIN = uuid4()


def text_context(tax: LcTaxonomy, body: str = "Un texto breve de opinión.") -> ContextContent:
    return ContextContent(
        kind=ContextKind.TEXT,
        title="Desconectar para aprender",
        body_md=body,
        text_type_node_id=tax.text_type.id,
    )


def item_content(tax: LcTaxonomy, stem: str) -> ItemContent:
    return ItemContent(
        difficulty=Difficulty.LOW,
        stem_md=stem,
        explanation_md="Se apoya en el texto.",
        taxonomy=TaxonomyTags(
            competence_id=tax.competence.id,
            assertion_id=tax.assertion.id,
            evidence_id=tax.evidence.id,
        ),
        options=tuple(
            Option(key=k, text=f"{stem} {k}", correct=k == "A", feedback=f"Por {k}") for k in "ABCD"
        ),
        context_code="LC-CTX-101",
    )


@pytest.fixture
def services(content_uow: UowFactory) -> tuple[Contexts, Authoring, Review]:
    clock = FixedClock(NOW)
    return (
        Contexts(uow_factory=content_uow, clock=clock),
        Authoring(uow_factory=content_uow, clock=clock),
        Review(uow_factory=content_uow, clock=clock),
    )


async def test_crear_un_contexto_valido(
    services: tuple[Contexts, Authoring, Review], lc_taxonomy: LcTaxonomy
) -> None:
    contexts, _, _ = services

    context = await contexts.create(
        code="LC-CTX-101", module="LC", content=text_context(lc_taxonomy), actor=TEACHER
    )

    assert context.current.number == 1
    assert context.current.word_count == 5
    assert context.current.created_by == TEACHER
    with pytest.raises(CodeTakenError):
        await contexts.create(
            code="LC-CTX-101", module="LC", content=text_context(lc_taxonomy), actor=TEACHER
        )


async def test_un_texto_de_501_palabras_no_se_guarda(
    services: tuple[Contexts, Authoring, Review], lc_taxonomy: LcTaxonomy
) -> None:
    contexts, _, _ = services

    with pytest.raises(ContentValidationError) as error:
        await contexts.create(
            code="LC-CTX-101",
            module="LC",
            content=text_context(lc_taxonomy, " ".join(["palabra"] * 501)),
            actor=TEACHER,
        )

    [issue] = error.value.issues
    assert issue.rule is ValidationRule.CONTEXT_WORD_LIMIT
    assert "501/500" in issue.message


async def test_una_imagen_sin_texto_alternativo_no_se_guarda(
    services: tuple[Contexts, Authoring, Review], lc_taxonomy: LcTaxonomy
) -> None:
    contexts, _, _ = services
    image = ContextContent(
        kind=ContextKind.IMAGE,
        title="Infografía",
        media_id=uuid4(),
        alt_text=" ",
        text_type_node_id=lc_taxonomy.text_type.id,
    )

    with pytest.raises(ContentValidationError) as error:
        await contexts.create(code="LC-CTX-102", module="LC", content=image, actor=TEACHER)

    assert {issue.rule for issue in error.value.issues} >= {
        ValidationRule.ALT_TEXT_REQUIRED,
        ValidationRule.INVALID_VALUE,  # la imagen no existe en el banco
    }


async def test_editar_versiona_y_propaga_a_los_items(
    services: tuple[Contexts, Authoring, Review],
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
) -> None:
    contexts, authoring, review = services
    await contexts.create(
        code="LC-CTX-101", module="LC", content=text_context(lc_taxonomy), actor=TEACHER
    )
    # LC-0101 publicado; LC-0102 en borrador; ambos usan el contexto.
    await authoring.create(
        code="LC-0101",
        module="LC",
        kind=ItemKind.SELECTION,
        content=item_content(lc_taxonomy, "Primero"),
        actor=TEACHER,
    )
    await authoring.submit("LC-0101", TEACHER, expected_revision=0)
    await review.approve(
        "LC-0101", ADMIN, expected_revision=1, confirms_alignment=True, confirms_originality=True
    )
    await authoring.create(
        code="LC-0102",
        module="LC",
        kind=ItemKind.SELECTION,
        content=item_content(lc_taxonomy, "Segundo"),
        actor=TEACHER,
    )

    details = await contexts.get("LC-CTX-101")
    assert (details.item_count, details.published_item_count) == (2, 1)

    context, result = await contexts.update(
        "LC-CTX-101",
        replace(text_context(lc_taxonomy), body_md="Texto corregido por el docente."),
        TEACHER,
        expected_revision=0,
    )

    assert context.current.number == 2
    assert context.revision == 1
    assert result.new_review_versions == ["LC-0101"]
    assert result.rebased_open_versions == ["LC-0102"]
    async with content_uow() as uow:
        published = await uow.items.get_by_code("LC-0101")
        draft = await uow.items.get_by_code("LC-0102")
        history = await uow.items.history("LC-0101")
    assert published is not None and published.published is not None
    assert published.open is not None and published.open.state is VersionState.IN_REVIEW
    assert published.open.context_version_id == context.current.id
    assert published.published.context_version_id != context.current.id
    assert history[-1].type.value == "context_changed"
    assert draft is not None and draft.open is not None
    assert draft.open.context_version_id == context.current.id


async def test_editar_exige_la_revision_vigente(
    services: tuple[Contexts, Authoring, Review], lc_taxonomy: LcTaxonomy
) -> None:
    contexts, _, _ = services
    await contexts.create(
        code="LC-CTX-101", module="LC", content=text_context(lc_taxonomy), actor=TEACHER
    )

    with pytest.raises(EditConflictError):
        await contexts.update(
            "LC-CTX-101", text_context(lc_taxonomy, "Otro"), TEACHER, expected_revision=4
        )
