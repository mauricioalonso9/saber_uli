"""T021: estados de un ítem y sus versiones (data-model §4 y §5; FR-010 a FR-016; R-02).

Un ítem tiene a lo sumo una versión publicada y una abierta (Borrador o En revisión). Nadie
aprueba una versión que creó o modificó (FR-012); aprobar exige las dos confirmaciones (FR-014);
devolver exige comentario, y rechazar o retirar, motivo. Cada transición sube la revisión del
ítem (R-09) y deja un evento de historia.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.errors import (
    ContentValidationError,
    InvalidTransitionError,
    SelfApprovalError,
)
from saber_uli.content.domain.events import HistoryEventType
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import Difficulty, ItemContent, ItemKind, VersionState
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.shared.domain.errors import RuleViolationError

T0 = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
AUTHOR = uuid4()
EDITOR = uuid4()
ADMIN = uuid4()
OTHER_ADMIN = uuid4()
H = HistoryEventType

CONTENT = ItemContent(difficulty=Difficulty.LOW, stem_md="Enunciado", explanation_md="Por qué")
ISSUE = ContentIssue("stem_md", ValidationRule.REQUIRED, "Escribe el enunciado.")


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def new_item(*, actor: UUID | None = AUTHOR, state: VersionState = VersionState.DRAFT) -> Item:
    return Item.create(
        code="LC-0001",
        module_code="LC",
        kind=ItemKind.SELECTION,
        origin=Origin.TEACHER,
        content=CONTENT,
        content_hash=b"h1",
        fingerprint=b"f1",
        context_version_id=None,
        actor=actor,
        now=T0,
        state=state,
    )


def published_item() -> Item:
    item = new_item()
    item.submit(AUTHOR, at(1))
    item.approve(ADMIN, at(2), confirms_alignment=True, confirms_originality=True)
    item.pull_events()
    return item


def events(item: Item) -> list[HistoryEventType]:
    return [event.type for event in item.pull_events()]


def test_crear_deja_un_borrador_con_el_autor_como_contribuyente() -> None:
    item = new_item()

    assert item.open is not None
    assert item.open.state is VersionState.DRAFT
    assert item.open.number == 1
    assert item.open.author_id == AUTHOR
    assert item.open.contributor_ids == {AUTHOR}
    assert item.published is None
    assert item.revision == 0
    assert events(item) == [H.CREATED]


def test_la_carga_del_sistema_no_tiene_autor_ni_contribuyentes() -> None:
    item = new_item(actor=None, state=VersionState.IN_REVIEW)

    assert item.open is not None
    assert item.open.author_id is None
    assert item.open.contributor_ids == frozenset()
    assert item.open.state is VersionState.IN_REVIEW


def test_editar_un_borrador_agrega_al_editor_y_sube_la_revision() -> None:
    item = new_item()
    item.pull_events()

    item.edit(replace(CONTENT, stem_md="Otro"), b"h2", b"f2", None, EDITOR, at(1))

    assert item.open is not None
    assert item.open.number == 1
    assert item.open.content.stem_md == "Otro"
    assert item.open.contributor_ids == {AUTHOR, EDITOR}
    assert item.revision == 1
    assert events(item) == [H.EDITED]


def test_enviar_exige_contenido_sin_problemas() -> None:
    item = new_item()

    with pytest.raises(ContentValidationError) as error:
        item.submit(AUTHOR, at(1), issues=[ISSUE])
    assert error.value.issues == (ISSUE,)

    item.submit(AUTHOR, at(1))
    assert item.open is not None
    assert item.open.state is VersionState.IN_REVIEW
    assert item.open.submitted_by == AUTHOR
    assert item.open.submitted_at == at(1)


def test_aprobar_publica_y_registra_al_revisor_y_las_confirmaciones() -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))
    item.pull_events()

    item.approve(ADMIN, at(2), confirms_alignment=True, confirms_originality=True)

    assert item.open is None
    assert item.published is not None
    assert item.published.state is VersionState.PUBLISHED
    assert item.published.reviewed_by == ADMIN
    assert item.published.published_at == at(2)
    [approved] = item.pull_events()
    assert approved.type is H.APPROVED
    assert approved.details == {"confirms_alignment": True, "confirms_originality": True}


@pytest.mark.parametrize("approver", [AUTHOR, EDITOR])
def test_nadie_aprueba_lo_que_creo_o_modifico(approver: UUID) -> None:
    item = new_item()
    item.edit(CONTENT, b"h1", b"f1", None, EDITOR, at(1))
    item.submit(EDITOR, at(2))

    with pytest.raises(SelfApprovalError):
        item.approve(approver, at(3), confirms_alignment=True, confirms_originality=True)
    assert item.can_approve(approver) is False
    assert item.can_approve(ADMIN) is True


@pytest.mark.parametrize(("alignment", "originality"), [(False, True), (True, False)])
def test_aprobar_exige_las_dos_confirmaciones(alignment: bool, originality: bool) -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))

    with pytest.raises(RuleViolationError):
        item.approve(ADMIN, at(2), confirms_alignment=alignment, confirms_originality=originality)


def test_devolver_vuelve_a_borrador_con_el_comentario() -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))
    item.pull_events()

    item.return_to_draft(ADMIN, at(2), "Revisa la opción C.")

    assert item.open is not None
    assert item.open.state is VersionState.DRAFT
    [returned] = item.pull_events()
    assert returned.type is H.RETURNED
    assert returned.comment == "Revisa la opción C."
    with pytest.raises(RuleViolationError):
        item.submit(AUTHOR, at(3))
        item.return_to_draft(ADMIN, at(4), "  ")


def test_rechazar_retira_la_version_sin_publicarla() -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))
    item.pull_events()

    item.reject(ADMIN, at(2), "Reproduce una pregunta del ICFES.")

    assert item.open is None
    assert item.published is None
    [rejected] = [version for version in item.versions if version.number == 1]
    assert rejected.state is VersionState.RETIRED
    assert rejected.retire_reason == "Reproduce una pregunta del ICFES."
    assert rejected.published_at is None
    assert events(item) == [H.REJECTED]


def test_retirar_una_publicada_exige_motivo() -> None:
    item = published_item()

    with pytest.raises(RuleViolationError):
        item.retire(ADMIN, at(3), "")
    item.retire(ADMIN, at(3), "Ambigua según las estadísticas.")

    assert item.published is None
    assert all(version.state is VersionState.RETIRED for version in item.versions)
    assert events(item) == [H.RETIRED]


def test_editar_lo_publicado_crea_una_version_nueva_y_la_publicada_sigue_vigente() -> None:
    item = published_item()

    item.edit(replace(CONTENT, stem_md="v2"), b"h2", b"f2", None, EDITOR, at(3))

    assert item.published is not None and item.published.number == 1
    assert item.published.content.stem_md == "Enunciado"
    assert item.open is not None
    assert (item.open.number, item.open.state) == (2, VersionState.DRAFT)
    assert item.open.author_id == EDITOR
    assert item.open.contributor_ids == {EDITOR}


def test_aprobar_la_version_nueva_retira_la_anterior_como_reemplazada() -> None:
    item = published_item()
    item.edit(replace(CONTENT, stem_md="v2"), b"h2", b"f2", None, EDITOR, at(3))
    item.submit(EDITOR, at(4))

    item.approve(ADMIN, at(5), confirms_alignment=True, confirms_originality=True)

    assert item.published is not None and item.published.number == 2
    [old] = [version for version in item.versions if version.number == 1]
    assert old.state is VersionState.RETIRED
    assert old.retired_at == at(5)
    assert old.retire_reason is not None
    assert H.SUPERSEDED in events(item)


@pytest.mark.parametrize(
    ("keep_in_review", "expected"), [(False, VersionState.DRAFT), (True, VersionState.IN_REVIEW)]
)
def test_editar_en_revision_vuelve_a_borrador_o_sigue_en_revision(
    keep_in_review: bool, expected: VersionState
) -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))

    item.edit(CONTENT, b"h1", b"f1", None, EDITOR, at(2), keep_in_review=keep_in_review)

    assert item.open is not None
    assert item.open.state is expected


def test_seguir_en_revision_exige_contenido_sin_problemas() -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))

    with pytest.raises(ContentValidationError):
        item.edit(CONTENT, b"h1", b"f1", None, EDITOR, at(2), keep_in_review=True, issues=[ISSUE])


def test_una_version_nueva_puede_nacer_en_revision() -> None:
    item = published_item()

    item.edit(
        CONTENT,
        b"h1",
        b"f1",
        None,
        None,
        at(3),
        start_state=VersionState.IN_REVIEW,
        event_type=H.CONTEXT_CHANGED,
    )

    assert item.open is not None
    assert item.open.state is VersionState.IN_REVIEW
    assert events(item) == [H.CONTEXT_CHANGED]


def test_editar_un_item_retirado_crea_una_version_nueva() -> None:
    item = published_item()
    item.retire(ADMIN, at(3), "Retirado")

    item.edit(CONTENT, b"h1", b"f1", None, EDITOR, at(4))

    assert item.open is not None and item.open.number == 2


@pytest.mark.parametrize(
    "action",
    [
        lambda item: item.submit(AUTHOR, at(9)),
        lambda item: item.approve(ADMIN, at(9), confirms_alignment=True, confirms_originality=True),
        lambda item: item.return_to_draft(ADMIN, at(9), "x"),
        lambda item: item.reject(ADMIN, at(9), "x"),
    ],
)
def test_transiciones_invalidas_sobre_un_publicado(action) -> None:  # type: ignore[no-untyped-def]
    item = published_item()

    with pytest.raises(InvalidTransitionError):
        action(item)


def test_retirar_sin_version_publicada_es_invalido() -> None:
    with pytest.raises(InvalidTransitionError):
        new_item().retire(ADMIN, at(1), "x")


def test_comentar_no_cambia_el_estado_ni_la_revision() -> None:
    item = new_item()
    item.pull_events()

    item.comment(EDITOR, at(1), "¿La opción B es ambigua?")

    assert item.revision == 0
    assert item.open is not None and item.open.state is VersionState.DRAFT
    [commented] = item.pull_events()
    assert (commented.type, commented.comment, commented.actor_id) == (
        H.COMMENTED,
        "¿La opción B es ambigua?",
        EDITOR,
    )


def test_cada_transicion_sube_la_revision() -> None:
    item = new_item()
    item.submit(AUTHOR, at(1))
    item.return_to_draft(ADMIN, at(2), "Ajusta")
    item.submit(AUTHOR, at(3))
    item.approve(ADMIN, at(4), confirms_alignment=True, confirms_originality=True)
    item.retire(OTHER_ADMIN, at(5), "Fin")

    assert item.revision == 5
