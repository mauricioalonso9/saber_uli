"""T019: huellas de contenido (research R-06).

- `content_hash`: igualdad exacta de la forma canónica; decide "sin cambios" al reimportar
  (FR-035, SC-002, SC-008).
- `fingerprint`: igualdad del texto normalizado; detecta duplicados con otro código (FR-032).
"""

import unicodedata
from dataclasses import replace
from uuid import UUID

from saber_uli.content.domain.fingerprint import content_hash, fingerprint
from saber_uli.content.domain.item_version import Difficulty, ItemContent, Option
from saber_uli.content.domain.taxonomy import TaxonomyTags

ITEM = ItemContent(
    difficulty=Difficulty.LOW,
    stem_md="¿Qué indica la expresión «la vuelve más visible»?",
    explanation_md="El celular hace notar una distracción.",
    taxonomy=TaxonomyTags(assertion_id=UUID("01920000-0000-7000-8000-000000000001")),
    options=(
        Option(key="A", text="Hace evidente una distracción.", correct=True, feedback="Correcto."),
        Option(key="B", text="Genera la distracción.", correct=False, feedback="Lo contrario."),
    ),
    context_code="LC-CTX-001",
)


def test_el_mismo_contenido_da_el_mismo_hash() -> None:
    assert content_hash(ITEM) == content_hash(replace(ITEM))
    assert len(content_hash(ITEM)) == 32


def test_el_orden_de_las_claves_no_importa() -> None:
    assert content_hash({"a": 1, "b": [1, 2]}) == content_hash({"b": [1, 2], "a": 1})


def test_espacios_externos_y_formas_unicode_no_cambian_el_hash() -> None:
    nfd = unicodedata.normalize("NFD", ITEM.stem_md)
    assert nfd != ITEM.stem_md

    assert content_hash(replace(ITEM, stem_md=f"  {nfd}\n")) == content_hash(ITEM)


def test_cambiar_una_retroalimentacion_cambia_el_hash() -> None:
    assert ITEM.options is not None
    changed = (replace(ITEM.options[0], feedback="Correcto, porque…"), ITEM.options[1])

    assert content_hash(replace(ITEM, options=changed)) != content_hash(ITEM)


def test_cambiar_la_dificultad_o_la_taxonomia_cambia_el_hash() -> None:
    assert content_hash(replace(ITEM, difficulty=Difficulty.HIGH)) != content_hash(ITEM)
    assert content_hash(replace(ITEM, taxonomy=TaxonomyTags())) != content_hash(ITEM)


def test_huella_igual_con_mayusculas_tildes_puntuacion_espacios_y_orden_de_opciones() -> None:
    original = fingerprint("¿Qué indica la expresión?", ["Opción uno", "Opción dos"], "Texto base")
    variant = fingerprint(
        "que   INDICA la expresion", ["opcion dos!", "OPCIÓN UNO"], "texto, base."
    )

    assert original == variant


def test_huella_distinta_si_cambia_el_texto_de_una_opcion_o_el_contexto() -> None:
    base = fingerprint("Enunciado", ["uno", "dos"], "contexto")

    assert fingerprint("Enunciado", ["uno", "tres"], "contexto") != base
    assert fingerprint("Enunciado", ["uno", "dos"], "otro contexto") != base
    assert fingerprint("Enunciado", ["uno", "dos"], None) != base
