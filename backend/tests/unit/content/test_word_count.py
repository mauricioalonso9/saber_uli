"""T015: conteo de palabras de los textos de Lectura crítica (FR-007; research R-10)."""

import json
from pathlib import Path

import pytest

from saber_uli.content.domain.word_count import count_words

SEED = Path(__file__).parents[3] / "seeds" / "banco_inicial_saber_uli.json"


def words(n: int) -> str:
    return " ".join(f"palabra{i}" for i in range(n))


def test_cuenta_palabras_separadas_por_espacios_y_puntuacion() -> None:
    assert count_words("Hola, mundo. ¿Cómo estás?") == 4


def test_quinientas_y_quinientas_una() -> None:
    assert count_words(words(500)) == 500
    assert count_words(words(501)) == 501


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("**negrita** y _cursiva_", 3),
        ("# Título\n\n> Una cita breve", 4),
        ("Lea [el reglamento](https://unilibre.edu.co/reglamento-de-equipos) hoy", 4),
        ("| Usuario | Plazo |\n|---|:---:|\n| Estudiante | 3 días |", 5),
        ("- uno\n- dos\n1. tres", 3),
    ],
)
def test_la_sintaxis_markdown_no_cuenta(markdown: str, expected: int) -> None:
    assert count_words(markdown) == expected


def test_numeros_tildes_y_palabras_con_guion_cuentan_como_una() -> None:
    assert count_words("En 2024 el franco-colombiano leyó 3,5 páginas") == 7


def test_un_texto_vacio_tiene_cero_palabras() -> None:
    assert count_words("") == 0
    assert count_words("  \n|---|\n  ") == 0


def test_los_contextos_de_lectura_critica_del_banco_inicial() -> None:
    bank = json.loads(SEED.read_text(encoding="utf-8"))
    contexts = [c for c in bank["contextos"] if c["modulo"] == "LC"]

    assert len(contexts) == 3
    for context in contexts:
        assert abs(count_words(context["contenido_md"]) - context["palabras"]) <= 2, context["id"]
