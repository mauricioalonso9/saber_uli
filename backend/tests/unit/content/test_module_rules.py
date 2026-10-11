"""T013: reglas de cada módulo y parte (FR-001 a FR-004, FR-045; data-model §1).

Las etiquetas obligatorias salen de los datos: un ítem lleva cada tipo de categoría que su módulo
tiene (competencia, afirmación, evidencia, componente, situación o parte). El tipo de texto es
de los contextos, no de los ítems.
"""

from dataclasses import replace
from uuid import uuid4

import pytest

from saber_uli.content.domain.module import QuestionType
from saber_uli.content.domain.rubric import (
    RelevanceCondition,
    Rubric,
    RubricDimension,
    RubricLevel,
)
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNodeKind, TaxonomyTags
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.shared.domain.errors import RuleViolationError
from tests.unit.content.taxonomy_fixtures import Ce, Ing, Lc, Rc

K = TaxonomyNodeKind


def lc_tags(**changes: object) -> TaxonomyTags:
    tags = TaxonomyTags(
        competence_id=Lc.competence.id, assertion_id=Lc.assertion.id, evidence_id=Lc.evidence.id
    )
    return replace(tags, **changes)  # type: ignore[arg-type]


def rules_of(issues: list) -> set[tuple[str, ValidationRule]]:  # type: ignore[type-arg]
    return {(issue.field, issue.rule) for issue in issues}


def test_las_etiquetas_obligatorias_salen_de_la_taxonomia_del_modulo() -> None:
    assert Lc.rules.required_tags == {K.COMPETENCE, K.ASSERTION, K.EVIDENCE}
    assert Rc.rules.required_tags == {
        K.COMPETENCE,
        K.ASSERTION,
        K.EVIDENCE,
        K.COMPONENT,
        K.SITUATION,
    }
    assert Ing.rules.required_tags == {K.PART}
    assert Ce.rules.required_tags == frozenset()


def test_etiquetas_completas_y_coherentes_no_tienen_problemas() -> None:
    assert Lc.rules.check_tags(lc_tags()) == []


@pytest.mark.parametrize("missing", ["competence_id", "assertion_id", "evidence_id"])
def test_falta_una_etiqueta_obligatoria(missing: str) -> None:
    issues = Lc.rules.check_tags(lc_tags(**{missing: None}))

    assert (f"taxonomy.{missing}", ValidationRule.REQUIRED) in rules_of(issues)


def test_razonamiento_cuantitativo_exige_componente_y_situacion() -> None:
    tags = TaxonomyTags(
        competence_id=Rc.competence.id, assertion_id=Rc.assertion.id, evidence_id=Rc.evidence.id
    )

    assert rules_of(Rc.rules.check_tags(tags)) == {
        ("taxonomy.component_id", ValidationRule.REQUIRED),
        ("taxonomy.situation_id", ValidationRule.REQUIRED),
    }


def test_un_codigo_de_otro_modulo_o_inexistente_es_desconocido() -> None:
    issues = Lc.rules.check_tags(lc_tags(evidence_id=Rc.evidence.id))
    unknown = Lc.rules.check_tags(lc_tags(assertion_id=uuid4()))

    assert ("taxonomy.evidence_id", ValidationRule.TAXONOMY_UNKNOWN) in rules_of(issues)
    assert ("taxonomy.assertion_id", ValidationRule.TAXONOMY_UNKNOWN) in rules_of(unknown)


def test_una_categoria_en_el_campo_de_otro_tipo_no_coincide() -> None:
    issues = Lc.rules.check_tags(lc_tags(evidence_id=Lc.assertion.id))

    assert ("taxonomy.evidence_id", ValidationRule.TAXONOMY_MISMATCH) in rules_of(issues)


def test_la_evidencia_pertenece_a_la_afirmacion_y_esta_a_la_competencia() -> None:
    issues = Lc.rules.check_tags(lc_tags(evidence_id=Lc.other_evidence.id))

    assert rules_of(issues) == {("taxonomy.evidence_id", ValidationRule.TAXONOMY_MISMATCH)}


def test_una_categoria_inactiva_no_sirve_en_un_item_nuevo_pero_si_en_uno_que_ya_la_usa() -> None:
    tags = lc_tags(evidence_id=Lc.inactive_evidence.id)

    assert rules_of(Lc.rules.check_tags(tags)) == {
        ("taxonomy.evidence_id", ValidationRule.TAXONOMY_INACTIVE)
    }
    assert Lc.rules.check_tags(tags, already_used=frozenset({Lc.inactive_evidence.id})) == []


@pytest.mark.parametrize(
    ("rules", "part", "expected"),
    [
        (Lc.rules, None, 4),
        (Rc.rules, None, 4),
        (Ing.rules, Ing.part1, 8),
        (Ing.rules, Ing.part2, 3),
        (Ing.rules, Ing.part6, 4),
    ],
)
def test_numero_de_opciones_por_modulo_y_parte(rules, part, expected) -> None:  # type: ignore[no-untyped-def]
    assert rules.option_count(None if part is None else part.id) == expected


def test_la_parte_1_de_ingles_es_de_emparejamiento() -> None:
    assert Ing.rules.part_format(Ing.part1.id) is PartFormat.MATCHING
    assert Ing.rules.part_format(Ing.part2.id) is PartFormat.SELECTION
    assert Ing.rules.part_format(None) is None


def test_ingles_exige_parte() -> None:
    issues = Ing.rules.check_tags(TaxonomyTags())

    assert rules_of(issues) == {("taxonomy.part_id", ValidationRule.REQUIRED)}


def test_comunicacion_escrita_es_de_escritura_y_conoce_sus_rubricas() -> None:
    assert Ce.module.question_type is QuestionType.WRITING
    assert Ce.rules.has_rubric(Ce.rubric_id)
    assert not Ce.rules.has_rubric(uuid4())
    assert Ce.rules.check_tags(TaxonomyTags()) == []


def test_una_rubrica_necesita_dimensiones_con_al_menos_dos_niveles() -> None:
    condition = RelevanceCondition(name="Pertinencia", description="Responde la pregunta")
    levels = (RubricLevel(level=1, description="Débil"), RubricLevel(level=2, description="Bien"))
    rubric = Rubric(
        id=uuid4(),
        code="RUB-CE-01",
        name="Rúbrica",
        relevance_condition=condition,
        dimensions=(RubricDimension(code="planteamiento", name="Planteamiento", levels=levels),),
    )

    assert rubric.active is True
    with pytest.raises(RuleViolationError):
        replace(rubric, dimensions=())
    with pytest.raises(RuleViolationError):
        replace(
            rubric,
            dimensions=(
                RubricDimension(
                    code="x", name="X", levels=(RubricLevel(level=1, description="."),)
                ),
            ),
        )
