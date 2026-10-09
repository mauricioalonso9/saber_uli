"""Conteo de palabras de los textos de Lectura crítica (FR-007; research R-10).

Cuenta lo que lee el estudiante, no la sintaxis Markdown: se quitan las URL de enlaces e
imágenes, las marcas de listas numeradas y los separadores de tabla. Una palabra es una secuencia
de letras o números; un guion, un apóstrofo, una coma o un punto entre dos de ellas no la parten
("franco-colombiano", "3,5").
"""

import re

_LINK_TARGET = re.compile(r"(!?\[[^\]]*\])\([^)]*\)")
_ORDERED_MARKER = re.compile(r"^\s*\d+[.)]\s+", flags=re.MULTILINE)
_WORD = re.compile(r"[^\W_]+(?:[-'2019.,][^\W_]+)*")

MAX_CONTEXT_WORDS = 500


def count_words(markdown: str) -> int:
    text = _LINK_TARGET.sub(r"\1", markdown)
    text = _ORDERED_MARKER.sub("", text)
    return len(_WORD.findall(text))
