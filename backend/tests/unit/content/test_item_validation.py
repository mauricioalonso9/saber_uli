"""T017: validación del contenido de ítems y contextos (FR-002 a FR-009, FR-024, FR-031).

Cada problema trae el campo, la regla del catálogo `ValidationRule` del contrato y un mensaje en
español. Un Borrador se puede guardar con problemas; enviar a revisión exige cero.
"""

from dataclasses import replace
from uuid import uuid4

import pytest

from saber_uli.content.domain.context import (
    ContextContent,
    ContextKind,
    SharedOption,
    validate_context,
)
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    Option,
    validate_item,
)
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from tests.unit.content.taxonomy_fixtures import Ce, Ing, Lc

R = ValidationRule


def found(issues: list[ContentIssue]) -> set[tuple[str, ValidationRule]]:
    return {(issue.field, issue.rule) for issue in issues}


def options(correct: str = "A", keys: str = "ABCD") -> tuple[Option, ...]:
    return tuple(
        Option(key=key, text=f"Opción {key}", correct=key in correct, feedback=f"Por qué {key}")
        for key in keys
    )


LC_TAGS = TaxonomyTags(
    competence_id=Lc.competence.id, assertion_id=Lc.assertion.id, evidence_id=Lc.evidence.id
)
LC_CONTEXT = ContextContent(
    kind=ContextKind.TEXT,
    title="Desconectar para aprender",
    body_md="Un texto breve de opinión.",
    text_type_node_id=Lc.text_type.id,
)
LC_ITEM = ItemContent(
    difficulty=Difficulty.LOW,
    stem_md="¿Qué indica la expresión?",
    explanation_md="La respuesta se apoya en el segundo párrafo.",
    taxonomy=LC_TAGS,
    options=options(),
    context_code="LC-CTX-001",
)
P1_CONTEXT = ContextContent(
    kind=ContextKind.SHARED_OPTIONS,
    title="Part 1",
    body_md="Match the descriptions with the words.",
    part_node_id=Ing.part1.id,
    shared_options=tuple(
        SharedOption(key=key, text=f"word {key}", feedback=f"«{key}» significa…")
        for key in "ABCDEFGH"
    ),
)
P1_ITEM = ItemContent(
    difficulty=Difficulty.LOW,
    stem_md="1. You use this to keep money.",
    explanation_md="«Wallet» es la billetera.",
    taxonomy=TaxonomyTags(part_id=Ing.part1.id),
    answer_key="H",
    context_code="ING-CTX-P1-001",
)


def lc(item: ItemContent = LC_ITEM, **kwargs: object) -> list[ContentIssue]:
    return validate_item(ItemKind.SELECTION, item, Lc.rules, context=LC_CONTEXT, **kwargs)  # type: ignore[arg-type]


def test_un_item_completo_de_lectura_critica_no_tiene_problemas() -> None:
    assert lc() == []


@pytest.mark.parametrize("correct", ["", "AB"])
def test_exactamente_una_opcion_correcta(correct: str) -> None:
    issues = lc(replace(LC_ITEM, options=options(correct=correct)))

    assert ("options", R.SINGLE_CORRECT_OPTION) in found(issues)


@pytest.mark.parametrize("keys", ["ABC", "ABCDE"])
def test_numero_de_opciones_del_modulo(keys: str) -> None:
    issues = lc(replace(LC_ITEM, options=options(keys=keys)))

    assert ("options", R.OPTION_COUNT) in found(issues)


def test_las_claves_van_en_orden_desde_a() -> None:
    issues = lc(replace(LC_ITEM, options=options(keys="ABDC")))

    assert ("options", R.OPTION_COUNT) in found(issues)


def test_cada_opcion_tiene_retroalimentacion() -> None:
    sin = tuple(
        replace(option, feedback="  ") if option.key == "B" else option for option in options()
    )

    assert found(lc(replace(LC_ITEM, options=sin))) == {
        ("options[B].feedback", R.OPTION_FEEDBACK_REQUIRED)
    }


def test_enunciado_y_explicacion_obligatorios() -> None:
    issues = lc(replace(LC_ITEM, stem_md=" ", explanation_md=""))

    assert found(issues) == {("stem_md", R.REQUIRED), ("explanation_md", R.EXPLANATION_REQUIRED)}


def test_las_etiquetas_se_validan_con_la_taxonomia_del_modulo() -> None:
    issues = lc(replace(LC_ITEM, taxonomy=replace(LC_TAGS, evidence_id=Lc.inactive_evidence.id)))

    assert found(issues) == {("taxonomy.evidence_id", R.TAXONOMY_INACTIVE)}
    assert (
        lc(
            replace(LC_ITEM, taxonomy=replace(LC_TAGS, evidence_id=Lc.inactive_evidence.id)),
            already_used=frozenset({Lc.inactive_evidence.id}),
        )
        == []
    )


def test_un_contexto_que_no_existe() -> None:
    issues = validate_item(ItemKind.SELECTION, LC_ITEM, Lc.rules, context=None)

    assert found(issues) == {("context_code", R.CONTEXT_UNKNOWN)}


def test_emparejamiento_valido_de_la_parte_1() -> None:
    assert validate_item(ItemKind.MATCHING, P1_ITEM, Ing.rules, context=P1_CONTEXT) == []


def test_la_clave_del_emparejamiento_debe_estar_entre_las_opciones_del_contexto() -> None:
    issues = validate_item(
        ItemKind.MATCHING, replace(P1_ITEM, answer_key="Z"), Ing.rules, context=P1_CONTEXT
    )

    assert found(issues) == {("answer_key", R.MATCHING_KEY_UNKNOWN)}


def test_el_emparejamiento_no_lleva_opciones_propias_y_admite_cinco_por_contexto() -> None:
    with_options = validate_item(
        ItemKind.MATCHING,
        replace(P1_ITEM, options=options(keys="ABC")),
        Ing.rules,
        context=P1_CONTEXT,
    )
    sixth = validate_item(
        ItemKind.MATCHING, P1_ITEM, Ing.rules, context=P1_CONTEXT, matching_siblings=5
    )

    assert ("options", R.OPTION_COUNT) in found(with_options)
    assert found(sixth) == {("context_code", R.OPTION_COUNT)}


def test_partes_de_seleccion_de_ingles_con_tres_o_cuatro_opciones() -> None:
    part2 = ItemContent(
        difficulty=Difficulty.MEDIUM,
        stem_md="Where can you see this notice?",
        explanation_md="En una biblioteca.",
        taxonomy=TaxonomyTags(part_id=Ing.part2.id),
        options=options(keys="ABC"),
    )

    assert validate_item(ItemKind.SELECTION, part2, Ing.rules, context=None) == []
    four = validate_item(
        ItemKind.SELECTION, replace(part2, options=options()), Ing.rules, context=None
    )
    assert ("options", R.OPTION_COUNT) in found(four)


def test_un_item_de_seleccion_no_puede_ir_en_la_parte_de_emparejamiento() -> None:
    issues = validate_item(
        ItemKind.SELECTION,
        replace(P1_ITEM, answer_key=None, options=options(keys="ABCDEFGH")),
        Ing.rules,
        context=P1_CONTEXT,
    )

    assert ("taxonomy.part_id", R.TAXONOMY_MISMATCH) in found(issues)


def test_consigna_de_escritura_con_rubrica_y_contexto() -> None:
    prompt = ItemContent(
        difficulty=Difficulty.MEDIUM,
        stem_md="¿Está de acuerdo? Escriba un texto argumentativo.",
        explanation_md="Se espera una postura clara con razones.",
        prompt_context_md="Varias universidades evalúan permitir la IA.",
        rubric_id=Ce.rubric_id,
    )

    assert validate_item(ItemKind.WRITING_PROMPT, prompt, Ce.rules, context=None) == []
    assert found(
        validate_item(
            ItemKind.WRITING_PROMPT, replace(prompt, rubric_id=uuid4()), Ce.rules, context=None
        )
    ) == {("rubric_id", R.RUBRIC_UNKNOWN)}
    assert found(
        validate_item(
            ItemKind.WRITING_PROMPT,
            replace(prompt, rubric_id=None, prompt_context_md=None, options=options()),
            Ce.rules,
            context=None,
        )
    ) == {
        ("rubric_id", R.REQUIRED),
        ("prompt_context_md", R.REQUIRED),
        ("options", R.OPTION_COUNT),
    }


# ------------------------------------------------------------------------------- contextos


def test_un_contexto_de_lectura_critica_completo() -> None:
    assert validate_context(LC_CONTEXT, Lc.rules) == []


def test_un_texto_de_lectura_critica_de_501_palabras() -> None:
    long = replace(LC_CONTEXT, body_md=" ".join(["palabra"] * 501))
    issues = validate_context(long, Lc.rules)

    assert found(issues) == {("body_md", R.CONTEXT_WORD_LIMIT)}
    assert "501/500" in issues[0].message
    assert validate_context(replace(long, body_md=" ".join(["palabra"] * 500)), Lc.rules) == []


def test_lectura_critica_exige_tipo_de_texto() -> None:
    issues = validate_context(replace(LC_CONTEXT, text_type_node_id=None), Lc.rules)

    assert found(issues) == {("text_type_node_id", R.REQUIRED)}


def test_una_imagen_exige_texto_alternativo() -> None:
    image = ContextContent(
        kind=ContextKind.IMAGE,
        title="Aviso",
        media_id=uuid4(),
        alt_text=" ",
        part_node_id=Ing.part2.id,
    )

    assert found(validate_context(image, Ing.rules)) == {("alt_text", R.ALT_TEXT_REQUIRED)}
    assert validate_context(replace(image, alt_text="Aviso de silencio"), Ing.rules) == []
    assert ("media_id", R.REQUIRED) in found(
        validate_context(replace(image, media_id=None, alt_text="Aviso"), Ing.rules)
    )


def test_las_opciones_compartidas_de_la_parte_1_son_exactamente_ocho() -> None:
    assert validate_context(P1_CONTEXT, Ing.rules) == []
    seven = replace(P1_CONTEXT, shared_options=P1_CONTEXT.shared_options[:7])  # type: ignore[index]

    assert found(validate_context(seven, Ing.rules)) == {("shared_options", R.OPTION_COUNT)}


def test_cada_opcion_compartida_tiene_retroalimentacion() -> None:
    assert P1_CONTEXT.shared_options is not None
    without = tuple(
        replace(option, feedback="") if option.key == "C" else option
        for option in P1_CONTEXT.shared_options
    )

    assert found(validate_context(replace(P1_CONTEXT, shared_options=without), Ing.rules)) == {
        ("shared_options[C].feedback", R.OPTION_FEEDBACK_REQUIRED)
    }


def test_ingles_exige_parte_en_el_contexto() -> None:
    issues = validate_context(replace(P1_CONTEXT, part_node_id=None), Ing.rules)

    assert ("part_node_id", R.REQUIRED) in found(issues)
