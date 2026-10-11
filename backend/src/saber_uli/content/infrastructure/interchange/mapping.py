"""Traducción entre el formato v1 (español) y las especificaciones de la aplicación.

Equivalencias (data-model §6): dificultad `baja/media/alta` → `low/medium/high`; estado
`borrador/en_revision/publicado/retirado` → `draft/in_review/published/retired`; origen
`ia/docente/banco_inicial` → `ai/teacher/seed`; `usa_opciones_del_contexto` → emparejamiento;
consigna → `writing_prompt`. Las partes de Inglés se identifican como `ING-P<n>`.
"""

import re
from decimal import Decimal
from typing import Any

from saber_uli.content.application.bundle import ContextSpec, ItemSpec, ModuleSpec, NodeSpec
from saber_uli.content.domain.context import ContextKind, Origin, SharedOption
from saber_uli.content.domain.item_version import Difficulty, ItemKind, Option, VersionState
from saber_uli.content.domain.module import Module, QuestionType
from saber_uli.content.domain.rubric import (
    RelevanceCondition,
    Rubric,
    RubricDimension,
    RubricLevel,
)
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNodeKind
from saber_uli.content.infrastructure.interchange import models as m

K = TaxonomyNodeKind

DIFFICULTY = {"baja": Difficulty.LOW, "media": Difficulty.MEDIUM, "alta": Difficulty.HIGH}
STATE = {
    "borrador": VersionState.DRAFT,
    "en_revision": VersionState.IN_REVIEW,
    "publicado": VersionState.PUBLISHED,
    "retirado": VersionState.RETIRED,
}
ORIGIN = {"ia": Origin.AI, "docente": Origin.TEACHER, "banco_inicial": Origin.SEED}
QUESTION_TYPE = {
    "seleccion_multiple_unica_respuesta": QuestionType.SELECTION,
    "abierta_texto_argumentativo": QuestionType.WRITING,
}
CONTEXT_KIND = {
    "texto": ContextKind.TEXT,
    "tabla": ContextKind.TABLE,
    "imagen": ContextKind.IMAGE,
    "opciones_compartidas": ContextKind.SHARED_OPTIONS,
}
PART_FORMAT = {"emparejamiento": PartFormat.MATCHING, "seleccion": PartFormat.SELECTION}
DEFAULT_BANK_TARGET = {"ING": 225, "CE": 20}
DEFAULT_TARGET = 150

_TABLE = re.compile(r"^\s*\|.*\|\s*$\n^\s*\|[\s:|-]+\|\s*$", flags=re.MULTILINE)


def _inverse[T](mapping: dict[str, T]) -> dict[T, str]:
    return {value: key for key, value in mapping.items()}


def part_code(number: int) -> str:
    return f"ING-P{number}"


def part_number(code: str) -> int | None:
    match = re.fullmatch(r"ING-P(\d)", code)
    return None if match is None else int(match.group(1))


def humanize(code: str) -> str:
    return code.replace("_", " ").capitalize()


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


# ------------------------------------------------------------------------------- lectura


def module_spec(
    model: m.Modulo, position: int, exam_questions: dict[str, Any] | None
) -> ModuleSpec:
    restrictions = model.restricciones or {}
    max_words = restrictions.get("max_palabras_texto")
    questions = model.preguntas_examen or int((exam_questions or {}).get(model.codigo, 0))
    module = Module(
        code=model.codigo,
        name=model.nombre,
        question_type=QUESTION_TYPE[model.tipo_pregunta],
        options_per_item=model.opciones_por_item,
        max_context_words=int(max_words) if isinstance(max_words, int) else None,
        exam_questions=questions,
        bank_target=model.meta_banco or DEFAULT_BANK_TARGET.get(model.codigo, DEFAULT_TARGET),
        position=position,
    )
    nodes: list[NodeSpec] = []

    def add(**kwargs: Any) -> None:
        nodes.append(NodeSpec(module_code=model.codigo, position=len(nodes) + 1, **kwargs))

    for competence in model.competencias:
        add(
            kind=K.COMPETENCE,
            code=competence.codigo,
            name=competence.nombre,
            target_weight=_decimal(competence.peso_aprox),
        )
        for assertion in competence.afirmaciones:
            add(
                kind=K.ASSERTION,
                code=assertion.codigo,
                name=assertion.descripcion,
                parent_code=competence.codigo,
                target_weight=_decimal(assertion.peso_aprox),
            )
            for evidence in assertion.evidencias:
                add(
                    kind=K.EVIDENCE,
                    code=evidence.codigo,
                    name=evidence.descripcion,
                    parent_code=assertion.codigo,
                )
    for kind, entries in ((K.COMPONENT, model.componentes), (K.SITUATION, model.situaciones)):
        for entry in entries:
            if isinstance(entry, str):
                add(kind=kind, code=entry, name=humanize(entry))
            else:
                add(kind=kind, code=entry.codigo, name=entry.nombre)
    for code, weight in model.tipos_texto.items():
        add(kind=K.TEXT_TYPE, code=code, name=humanize(code), target_weight=_decimal(weight))
    for part in model.partes:
        part_format = (
            PART_FORMAT[part.formato]
            if part.formato is not None
            else (PartFormat.MATCHING if part.opciones > 4 else PartFormat.SELECTION)
        )
        add(
            kind=K.PART,
            code=part_code(part.parte),
            name=part.tarea,
            target_weight=_decimal(part.peso_aprox),
            part_options=part.opciones,
            part_format=part_format,
        )
    return ModuleSpec(module=module, nodes=tuple(nodes))


def context_spec(model: m.Contexto) -> ContextSpec:
    if model.tipo is not None:
        kind = CONTEXT_KIND[model.tipo]
    elif model.opciones_compartidas is not None:
        kind = ContextKind.SHARED_OPTIONS
    elif model.imagen is not None:
        kind = ContextKind.IMAGE
    elif model.contenido_md and _TABLE.search(model.contenido_md):
        kind = ContextKind.TABLE
    else:
        kind = ContextKind.TEXT
    return ContextSpec(
        code=model.id,
        module_code=model.modulo,
        kind=kind,
        title=model.titulo,
        origin=ORIGIN[model.origen],
        body_md=model.contenido_md,
        media_id=None if model.imagen is None else model.imagen.media_id,
        alt_text=None if model.imagen is None else model.imagen.texto_alternativo,
        text_type_code=model.tipo_texto,
        part_code=None if model.parte is None else part_code(model.parte),
        subtype=model.subtipo,
        shared_options=None
        if model.opciones_compartidas is None
        else tuple(
            SharedOption(key=o.clave, text=o.texto, feedback=o.retroalimentacion)
            for o in model.opciones_compartidas
        ),
        state=None if model.estado is None else STATE[model.estado],
    )


def item_spec(model: m.Item) -> ItemSpec:
    tags: dict[TaxonomyNodeKind, str] = {}
    for kind, code in (
        (K.COMPETENCE, model.competencia),
        (K.ASSERTION, model.afirmacion),
        (K.EVIDENCE, model.evidencia),
        (K.COMPONENT, model.componente),
        (K.SITUATION, model.situacion),
        (K.PART, None if model.parte is None else part_code(model.parte)),
    ):
        if code is not None:
            tags[kind] = code
    return ItemSpec(
        code=model.id,
        module_code=model.modulo,
        kind=ItemKind.MATCHING if model.usa_opciones_del_contexto else ItemKind.SELECTION,
        difficulty=DIFFICULTY[model.dificultad],
        stem_md=model.enunciado,
        explanation_md=model.explicacion,
        origin=ORIGIN[model.origen],
        tags=tags,
        options=None
        if model.opciones is None
        else tuple(
            Option(key=o.clave, text=o.texto, correct=o.correcta, feedback=o.retroalimentacion)
            for o in model.opciones
        ),
        answer_key=model.clave_correcta,
        context_code=model.contexto_id,
        state=None if model.estado is None else STATE[model.estado],
        version=model.version,
    )


def prompt_spec(model: m.Consigna) -> ItemSpec:
    return ItemSpec(
        code=model.id,
        module_code=model.modulo,
        kind=ItemKind.WRITING_PROMPT,
        difficulty=DIFFICULTY[model.dificultad],
        stem_md=model.pregunta,
        explanation_md=model.explicacion,
        origin=ORIGIN[model.origen],
        prompt_context_md=model.contexto,
        rubric_code=model.rubrica_id,
        state=None if model.estado is None else STATE[model.estado],
        version=model.version,
    )


def rubric(model: m.Rubrica) -> Rubric:
    return Rubric(
        id=None,
        code=model.id,
        name=model.nombre,
        note=model.nota,
        relevance_condition=RelevanceCondition(
            name=model.condicion_previa.nombre, description=model.condicion_previa.descripcion
        ),
        dimensions=tuple(
            RubricDimension(
                code=d.codigo,
                name=d.nombre,
                levels=tuple(
                    RubricLevel(level=n.nivel, description=n.descripcion) for n in d.niveles
                ),
            )
            for d in model.dimensiones
        ),
    )


# ------------------------------------------------------------------------------- escritura

_DIFFICULTY_OUT = _inverse(DIFFICULTY)
_STATE_OUT = _inverse(STATE)
_ORIGIN_OUT = _inverse(ORIGIN)
_QUESTION_TYPE_OUT = _inverse(QUESTION_TYPE)
_CONTEXT_KIND_OUT = _inverse(CONTEXT_KIND)
_PART_FORMAT_OUT = _inverse(PART_FORMAT)


def _weight(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def module_out(spec: ModuleSpec) -> dict[str, Any]:
    module = spec.module
    out: dict[str, Any] = {
        "codigo": module.code,
        "nombre": module.name,
        "tipo_pregunta": _QUESTION_TYPE_OUT[module.question_type],
        "preguntas_examen": module.exam_questions,
        "meta_banco": module.bank_target,
    }
    if module.options_per_item is not None:
        out["opciones_por_item"] = module.options_per_item
    if module.max_context_words is not None:
        out["restricciones"] = {"max_palabras_texto": module.max_context_words}
    by_kind: dict[TaxonomyNodeKind, list[NodeSpec]] = {}
    for node in spec.nodes:
        by_kind.setdefault(node.kind, []).append(node)
    competences = []
    for competence in by_kind.get(K.COMPETENCE, []):
        assertions = []
        for assertion in by_kind.get(K.ASSERTION, []):
            if assertion.parent_code != competence.code:
                continue
            entry: dict[str, Any] = {"codigo": assertion.code, "descripcion": assertion.name}
            if assertion.target_weight is not None:
                entry["peso_aprox"] = _weight(assertion.target_weight)
            entry["evidencias"] = [
                {"codigo": evidence.code, "descripcion": evidence.name}
                for evidence in by_kind.get(K.EVIDENCE, [])
                if evidence.parent_code == assertion.code
            ]
            assertions.append(entry)
        competence_out: dict[str, Any] = {"codigo": competence.code, "nombre": competence.name}
        if competence.target_weight is not None:
            competence_out["peso_aprox"] = _weight(competence.target_weight)
        competence_out["afirmaciones"] = assertions
        competences.append(competence_out)
    if competences:
        out["competencias"] = competences
    for kind, key in ((K.COMPONENT, "componentes"), (K.SITUATION, "situaciones")):
        if kind in by_kind:
            out[key] = [
                node.code
                if node.name == humanize(node.code)
                else {"codigo": node.code, "nombre": node.name}
                for node in by_kind[kind]
            ]
    if K.TEXT_TYPE in by_kind:
        out["tipos_texto"] = {
            node.code: _weight(node.target_weight) or 0.0 for node in by_kind[K.TEXT_TYPE]
        }
    if K.PART in by_kind:
        parts = []
        for node in by_kind[K.PART]:
            number = part_number(node.code)
            part: dict[str, Any] = {
                "parte": number,
                "opciones": node.part_options,
                "tarea": node.name,
            }
            if node.target_weight is not None:
                part["peso_aprox"] = _weight(node.target_weight)
            if node.part_format is not None:
                part["formato"] = _PART_FORMAT_OUT[node.part_format]
            parts.append(part)
        out["partes"] = parts
    return out


def context_out(spec: ContextSpec) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": spec.code,
        "modulo": spec.module_code,
        "titulo": spec.title,
        "tipo": _CONTEXT_KIND_OUT[spec.kind],
    }
    if spec.body_md is not None:
        out["contenido_md"] = spec.body_md
    if spec.text_type_code is not None:
        out["tipo_texto"] = spec.text_type_code
    if spec.subtype is not None:
        out["subtipo"] = spec.subtype
    if spec.part_code is not None:
        out["parte"] = part_number(spec.part_code)
    if spec.shared_options is not None:
        out["opciones_compartidas"] = [
            {"clave": o.key, "texto": o.text, "retroalimentacion": o.feedback}
            for o in spec.shared_options
        ]
    if spec.media_id is not None:
        out["imagen"] = {"media_id": str(spec.media_id), "texto_alternativo": spec.alt_text or ""}
    out["origen"] = _ORIGIN_OUT[spec.origin]
    if spec.state is not None:
        out["estado"] = _STATE_OUT[spec.state]
    return out


_TAG_FIELDS = {
    K.COMPETENCE: "competencia",
    K.ASSERTION: "afirmacion",
    K.EVIDENCE: "evidencia",
    K.COMPONENT: "componente",
    K.SITUATION: "situacion",
}


def item_out(spec: ItemSpec) -> dict[str, Any]:
    base: dict[str, Any] = {"id": spec.code}
    if spec.version is not None:
        base["version"] = spec.version
    base["modulo"] = spec.module_code
    base["dificultad"] = _DIFFICULTY_OUT[spec.difficulty]
    if spec.kind is ItemKind.WRITING_PROMPT:
        base["contexto"] = spec.prompt_context_md or ""
        base["pregunta"] = spec.stem_md
        base["rubrica_id"] = spec.rubric_code or ""
        if spec.explanation_md:
            base["explicacion"] = spec.explanation_md
    else:
        base["contexto_id"] = spec.context_code
        for kind, field in _TAG_FIELDS.items():
            if kind in spec.tags:
                base[field] = spec.tags[kind]
        if K.PART in spec.tags:
            base["parte"] = part_number(spec.tags[K.PART])
        base["enunciado"] = spec.stem_md
        if spec.kind is ItemKind.MATCHING:
            base["usa_opciones_del_contexto"] = True
            base["clave_correcta"] = spec.answer_key
        if spec.options is not None:
            base["opciones"] = [
                {
                    "clave": o.key,
                    "texto": o.text,
                    "correcta": o.correct,
                    "retroalimentacion": o.feedback,
                }
                for o in spec.options
            ]
        base["explicacion"] = spec.explanation_md
    base["origen"] = _ORIGIN_OUT[spec.origin]
    if spec.state is not None:
        base["estado"] = _STATE_OUT[spec.state]
    return base


def rubric_out(value: Rubric) -> dict[str, Any]:
    out: dict[str, Any] = {"id": value.code, "nombre": value.name}
    if value.note is not None:
        out["nota"] = value.note
    out["condicion_previa"] = {
        "nombre": value.relevance_condition.name,
        "descripcion": value.relevance_condition.description,
    }
    out["dimensiones"] = [
        {
            "codigo": d.code,
            "nombre": d.name,
            "niveles": [{"nivel": n.level, "descripcion": n.description} for n in d.levels],
        }
        for d in value.dimensions
    ]
    return out
