"""ETag e If-Match del banco de ítems (research R-09; FR-027).

La revisión de un ítem o contexto es su `ETag` (`"7"`). Las modificaciones exigen `If-Match`:
sin él o mal formado, 428 `precondition-required`; si no coincide, 412 `edit-conflict` con el
recurso actual (`current`) y su `etag`, para que la interfaz muestre las dos versiones y la persona
decida.
"""

import re
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Header

from saber_uli.shared.api.problems import ProblemException

_ETAG = re.compile(r'^\s*(?:W/)?"(\d{1,9})"\s*$')


def etag(revision: int) -> str:
    return f'"{revision}"'


def expected_revision(if_match: str | None) -> int:
    if if_match is None or not if_match.strip():
        raise ProblemException(
            428,
            "precondition-required",
            detail="Falta la versión que estás editando (If-Match).",
        )
    match = _ETAG.match(if_match)
    if match is None:
        # Mal formado no es "otra versión": falta una precondición válida.
        raise ProblemException(
            428, "precondition-required", detail="La versión indicada (If-Match) no es válida."
        )
    return int(match.group(1))


def edit_conflict(current: Any, *, revision: int) -> ProblemException:
    return ProblemException(
        412,
        "edit-conflict",
        detail="Otra persona cambió este contenido mientras lo editabas.",
        extensions={"current": current, "etag": etag(revision)},
    )


def require_revision(
    if_match: str | None, actual: int, *, current: Callable[[], Any] | None = None
) -> None:
    """Compara `If-Match` con la revisión actual; `current` arma el cuerpo del conflicto."""
    if expected_revision(if_match) != actual:
        raise edit_conflict(None if current is None else current(), revision=actual)


async def if_match_revision(
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> int:
    """Dependencia de FastAPI: la revisión que el cliente editó."""
    return expected_revision(if_match)
