"""Taxonomía en memoria para las pruebas del dominio `content` (forma del banco inicial)."""

from decimal import Decimal
from uuid import UUID, uuid4

from saber_uli.content.domain.module import Module, ModuleRules, QuestionType
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNode, TaxonomyNodeKind

K = TaxonomyNodeKind


def node(
    module: str,
    kind: TaxonomyNodeKind,
    code: str,
    *,
    parent: TaxonomyNode | None = None,
    active: bool = True,
    weight: str | None = None,
    part_options: int | None = None,
    part_format: PartFormat | None = None,
) -> TaxonomyNode:
    return TaxonomyNode(
        id=uuid4(),
        module_code=module,
        kind=kind,
        code=code,
        name=code,
        parent_id=None if parent is None else parent.id,
        target_weight=None if weight is None else Decimal(weight),
        part_options=part_options,
        part_format=part_format,
        active=active,
        position=0,
    )


class Lc:
    module = Module(
        code="LC",
        name="Lectura crítica",
        question_type=QuestionType.SELECTION,
        options_per_item=4,
        max_context_words=500,
        exam_questions=30,
        bank_target=150,
        position=1,
    )
    competence = node("LC", K.COMPETENCE, "LC-C1")
    assertion = node("LC", K.ASSERTION, "LC-A1", parent=competence, weight="0.26")
    evidence = node("LC", K.EVIDENCE, "LC-E1.1", parent=assertion)
    other_assertion = node("LC", K.ASSERTION, "LC-A2", parent=competence, weight="0.40")
    other_evidence = node("LC", K.EVIDENCE, "LC-E2.1", parent=other_assertion)
    inactive_evidence = node("LC", K.EVIDENCE, "LC-E1.9", parent=assertion, active=False)
    text_type = node("LC", K.TEXT_TYPE, "continuo_informativo")
    nodes = (
        competence,
        assertion,
        evidence,
        other_assertion,
        other_evidence,
        inactive_evidence,
        text_type,
    )
    rules = ModuleRules(module, nodes)


class Rc:
    module = Module(
        code="RC",
        name="Razonamiento cuantitativo",
        question_type=QuestionType.SELECTION,
        options_per_item=4,
        max_context_words=None,
        exam_questions=30,
        bank_target=150,
        position=2,
    )
    competence = node("RC", K.COMPETENCE, "RC-C1", weight="0.34")
    assertion = node("RC", K.ASSERTION, "RC-A1", parent=competence)
    evidence = node("RC", K.EVIDENCE, "RC-E1.1", parent=assertion)
    component = node("RC", K.COMPONENT, "RC-COMP-EST")
    situation = node("RC", K.SITUATION, "RC-SIT-FAM")
    nodes = (competence, assertion, evidence, component, situation)
    rules = ModuleRules(module, nodes)


class Ing:
    module = Module(
        code="ING",
        name="Inglés",
        question_type=QuestionType.SELECTION,
        options_per_item=None,
        max_context_words=None,
        exam_questions=45,
        bank_target=225,
        position=4,
    )
    part1 = node(
        "ING", K.PART, "ING-P1", weight="0.11", part_options=8, part_format=PartFormat.MATCHING
    )
    part2 = node(
        "ING", K.PART, "ING-P2", weight="0.11", part_options=3, part_format=PartFormat.SELECTION
    )
    part6 = node(
        "ING", K.PART, "ING-P6", weight="0.11", part_options=4, part_format=PartFormat.SELECTION
    )
    nodes = (part1, part2, part6)
    rules = ModuleRules(module, nodes)


class Ce:
    module = Module(
        code="CE",
        name="Comunicación escrita",
        question_type=QuestionType.WRITING,
        options_per_item=None,
        max_context_words=None,
        exam_questions=1,
        bank_target=20,
        position=5,
    )
    rubric_id: UUID = uuid4()
    rules = ModuleRules(module, (), rubric_ids=frozenset({rubric_id}))
