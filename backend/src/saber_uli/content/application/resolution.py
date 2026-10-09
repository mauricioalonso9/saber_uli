"""De especificaciones con códigos a contenido del dominio (carga del banco inicial e importación).

`Resolver` conoce la taxonomía, las rúbricas y los módulos de la base: traduce los códigos de las
especificaciones a identificadores y arma las reglas de cada módulo. Un código que no existe es un
problema del ítem o contexto (`taxonomy_unknown`, `rubric_unknown`), no un error del archivo.
"""

from collections.abc import Iterable
from uuid import UUID

from saber_uli.content.application.bundle import ContextSpec, ItemSpec
from saber_uli.content.domain.context import ContextContent
from saber_uli.content.domain.fingerprint import content_hash, fingerprint
from saber_uli.content.domain.item_version import ItemContent
from saber_uli.content.domain.module import Module, ModuleRules
from saber_uli.content.domain.rubric import Rubric
from saber_uli.content.domain.taxonomy import (
    TaxonomyNode,
    TaxonomyNodeKind,
    TaxonomyTags,
    field_for,
)
from saber_uli.content.domain.validation import ContentIssue, ValidationRule

R = ValidationRule


class Resolver:
    def __init__(
        self, modules: Iterable[Module], nodes: Iterable[TaxonomyNode], rubrics: Iterable[Rubric]
    ) -> None:
        node_list = list(nodes)
        rubric_list = list(rubrics)
        self._nodes = {node.code: node for node in node_list}
        self._rubrics = {rubric.code: rubric for rubric in rubric_list}
        active_rubrics = frozenset(r.id for r in rubric_list if r.active and r.id is not None)
        self.rules = {
            module.code: ModuleRules(module, node_list, rubric_ids=active_rubrics)
            for module in modules
        }

    def node_id(
        self, code: str | None, kind: TaxonomyNodeKind, field: str
    ) -> tuple[UUID | None, list[ContentIssue]]:
        if code is None:
            return None, []
        node = self._nodes.get(code)
        if node is None:
            return None, [
                ContentIssue(field, R.TAXONOMY_UNKNOWN, f"La categoría {code} no existe.")
            ]
        if node.kind is not kind:
            return None, [
                ContentIssue(field, R.TAXONOMY_MISMATCH, f"El código {code} no corresponde.")
            ]
        return node.id, []

    def context_content(self, spec: ContextSpec) -> tuple[ContextContent, list[ContentIssue]]:
        issues: list[ContentIssue] = []
        text_type, found = self.node_id(
            spec.text_type_code, TaxonomyNodeKind.TEXT_TYPE, "text_type_node_id"
        )
        issues += found
        part, found = self.node_id(spec.part_code, TaxonomyNodeKind.PART, "part_node_id")
        issues += found
        content = ContextContent(
            kind=spec.kind,
            title=spec.title,
            body_md=spec.body_md,
            media_id=spec.media_id,
            alt_text=spec.alt_text,
            text_type_node_id=text_type,
            part_node_id=part,
            subtype=spec.subtype,
            shared_options=spec.shared_options,
        )
        return content, issues

    def item_content(self, spec: ItemSpec) -> tuple[ItemContent, list[ContentIssue]]:
        issues: list[ContentIssue] = []
        tags: dict[str, UUID | None] = {}
        for kind, code in spec.tags.items():
            field = field_for(kind)
            node_id, found = self.node_id(code, kind, f"taxonomy.{field}")
            issues += found
            tags[field] = node_id
        rubric_id = None
        if spec.rubric_code is not None:
            rubric = self._rubrics.get(spec.rubric_code)
            if rubric is None:
                issues.append(
                    ContentIssue("rubric_id", R.RUBRIC_UNKNOWN, "La rúbrica indicada no existe.")
                )
            else:
                rubric_id = rubric.id
        content = ItemContent(
            difficulty=spec.difficulty,
            stem_md=spec.stem_md,
            explanation_md=spec.explanation_md,
            taxonomy=TaxonomyTags(**tags),
            options=spec.options,
            answer_key=spec.answer_key,
            prompt_context_md=spec.prompt_context_md,
            rubric_id=rubric_id,
            context_code=spec.context_code,
        )
        return content, issues


def item_hashes(content: ItemContent, context_text: str | None) -> tuple[bytes, bytes]:
    """`content_hash` del contenido y `fingerprint` del texto con su contexto (research R-06)."""
    options = [option.text for option in content.options or ()]
    stem = (
        content.stem_md
        if content.prompt_context_md is None
        else (f"{content.prompt_context_md}\n{content.stem_md}")
    )
    return content_hash(content), fingerprint(stem, options, context_text)


def context_text(content: ContextContent | None) -> str | None:
    """Texto del contexto que entra en la huella de los ítems que lo usan."""
    if content is None:
        return None
    shared = " ".join(f"{o.key} {o.text}" for o in content.shared_options or ())
    return " ".join(part for part in (content.body_md or "", shared) if part) or content.title
