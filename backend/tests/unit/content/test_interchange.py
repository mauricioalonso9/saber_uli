"""T025: formato de intercambio v1 (research R-03; data-model §6; ADR 0008).

El JSON del banco inicial es el formato de carga, importación y exportación. El lector entrega
especificaciones con códigos (la aplicación los resuelve contra la taxonomía) y separa los errores
de cada entrada: un ítem mal formado no invalida el archivo, pero un sobre ilegible sí.
"""

import json
from pathlib import Path

import pytest

from saber_uli.content.application.bundle import Bundle
from saber_uli.content.domain.context import ContextKind, Origin
from saber_uli.content.domain.item_version import Difficulty, ItemKind, VersionState
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNodeKind
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.content.infrastructure.interchange.json_format import (
    UnreadableFileError,
    read_bundle,
    write_bundle,
)

SEED = Path(__file__).parents[3] / "seeds" / "banco_inicial_saber_uli.json"
K = TaxonomyNodeKind


@pytest.fixture(scope="module")
def seed_bytes() -> bytes:
    return SEED.read_bytes()


@pytest.fixture(scope="module")
def seed(seed_bytes: bytes) -> Bundle:
    return read_bundle(seed_bytes)


def test_el_banco_inicial_se_lee_sin_errores(seed: Bundle) -> None:
    assert seed.schema_version == "1.0"
    assert seed.errors == []
    assert [spec.module.code for spec in seed.modules] == ["LC", "RC", "CC", "ING", "CE"]
    assert len(seed.contexts) == 8
    assert len(seed.items) == 46
    assert sum(item.kind is ItemKind.WRITING_PROMPT for item in seed.items) == 3
    assert [rubric.code for rubric in seed.rubrics] == ["RUB-CE-01"]


def test_equivalencias_del_formato(seed: Bundle) -> None:
    items = {item.code: item for item in seed.items}

    lc = items["LC-0001"]
    assert lc.difficulty is Difficulty.LOW
    assert lc.state is VersionState.IN_REVIEW
    assert lc.origin is Origin.AI
    assert lc.kind is ItemKind.SELECTION
    assert lc.tags == {K.COMPETENCE: "LC-C1", K.ASSERTION: "LC-A1", K.EVIDENCE: "LC-E1.1"}
    assert lc.context_code == "LC-CTX-001"
    assert lc.options is not None and sum(option.correct for option in lc.options) == 1

    matching = items["ING-0001"]
    assert matching.kind is ItemKind.MATCHING
    assert matching.answer_key == "H"
    assert matching.options is None
    assert matching.tags == {K.PART: "ING-P1"}

    rc = items["RC-0001"]
    assert rc.tags[K.COMPONENT] == "estadistica"
    assert rc.tags[K.SITUATION] == "comunitaria_social"

    prompt = items["CE-0001"]
    assert prompt.kind is ItemKind.WRITING_PROMPT
    assert prompt.rubric_code == "RUB-CE-01"
    assert prompt.prompt_context_md is not None


def test_la_taxonomia_de_cada_modulo(seed: Bundle) -> None:
    modules = {spec.module.code: spec for spec in seed.modules}

    lc = {node.code: node for node in modules["LC"].nodes}
    assert lc["LC-A1"].kind is K.ASSERTION and lc["LC-A1"].parent_code == "LC-C1"
    assert str(lc["LC-A1"].target_weight) == "0.26"
    assert lc["LC-E1.1"].parent_code == "LC-A1"
    assert lc["continuo_informativo"].kind is K.TEXT_TYPE
    assert modules["LC"].module.max_context_words == 500
    assert modules["LC"].module.exam_questions == 30

    rc = {node.code: node for node in modules["RC"].nodes}
    assert rc["RC-C1"].target_weight is not None
    assert rc["estadistica"].kind is K.COMPONENT
    assert rc["familiar_personal"].kind is K.SITUATION

    parts = {node.code: node for node in modules["ING"].nodes}
    assert (parts["ING-P1"].part_options, parts["ING-P1"].part_format) == (8, PartFormat.MATCHING)
    assert (parts["ING-P4"].part_options, parts["ING-P4"].part_format) == (3, PartFormat.SELECTION)
    assert modules["ING"].module.options_per_item is None

    assert modules["CE"].nodes == ()
    assert modules["CE"].module.exam_questions == 1


def test_contextos(seed: Bundle) -> None:
    contexts = {context.code: context for context in seed.contexts}

    table = contexts["LC-CTX-003"]
    assert table.kind is ContextKind.TABLE
    assert table.text_type_code == "discontinuo_informativo"
    shared = contexts["ING-CTX-P1-001"]
    assert shared.kind is ContextKind.SHARED_OPTIONS
    assert shared.part_code == "ING-P1"
    assert shared.shared_options is not None and len(shared.shared_options) == 8
    assert contexts["LC-CTX-001"].kind is ContextKind.TEXT


def test_escribir_y_volver_a_leer_da_el_mismo_banco(seed: Bundle) -> None:
    again = read_bundle(write_bundle(seed))

    assert again.modules == seed.modules
    assert again.contexts == seed.contexts
    assert again.items == seed.items
    assert again.rubrics == seed.rubrics


def test_un_item_mal_formado_es_un_error_de_esa_entrada(seed_bytes: bytes) -> None:
    bank = json.loads(seed_bytes)
    del bank["items"][0]["enunciado"]
    bank["items"][1]["dificultad"] = "facilisima"

    bundle = read_bundle(json.dumps(bank).encode())

    errors = {error.code: error for error in bundle.errors}
    assert set(errors) == {"LC-0001", "LC-0002"}
    assert ("enunciado", ValidationRule.REQUIRED) in {
        (issue.field, issue.rule) for issue in errors["LC-0001"].issues
    }
    assert ("dificultad", ValidationRule.INVALID_VALUE) in {
        (issue.field, issue.rule) for issue in errors["LC-0002"].issues
    }
    assert len(bundle.items) == 44


@pytest.mark.parametrize(
    "content",
    [
        b"no es json",
        b"[]",
        json.dumps({"esquema_version": "2.0", "items": []}).encode(),
        json.dumps({"items": []}).encode(),
        json.dumps({"esquema_version": "1.0", "items": {}}).encode(),
        "{}".encode("utf-16"),
    ],
)
def test_un_sobre_ilegible_invalida_el_archivo(content: bytes) -> None:
    with pytest.raises(UnreadableFileError):
        read_bundle(content)


# --- T035: entradas hostiles no producen errores internos -----------------------------------


def test_un_json_profundamente_anidado_es_ilegible_no_un_error_interno() -> None:
    nested = b'{"esquema_version": "1.0", "items": [' + b"[" * 100_000 + b"]" * 100_000 + b"]}"

    with pytest.raises(UnreadableFileError):
        read_bundle(nested)


@pytest.mark.parametrize("value", ["treinta", None, [30], {"x": 1}])
def test_preguntas_por_modulo_con_valores_raros_no_rompen_la_lectura(
    seed_bytes: bytes, value: object
) -> None:
    bank = json.loads(seed_bytes)
    bank["estructura_examen"]["preguntas_por_modulo"]["LC"] = value

    bundle = read_bundle(json.dumps(bank).encode())

    lc = next(spec for spec in bundle.modules if spec.module.code == "LC")
    assert lc.module.exam_questions == 0


def test_un_sobre_con_estructura_examen_que_no_es_objeto(seed_bytes: bytes) -> None:
    bank = json.loads(seed_bytes)
    bank["estructura_examen"] = "30 preguntas"

    with pytest.raises(UnreadableFileError):
        read_bundle(json.dumps(bank).encode())
