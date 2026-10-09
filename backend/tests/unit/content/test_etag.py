"""T027: ETag e If-Match del banco de ítems (research R-09; FR-027).

`ETag: "<revision>"`. Sin `If-Match` responde 428 `precondition-required`; si no coincide, 412
`edit-conflict` con el recurso actual (`current`) y su `etag` para que la interfaz muestre las dos
versiones. Se acepta el ETag débil `W/"7"`.
"""

from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI

from saber_uli.content.api.etag import (
    edit_conflict,
    etag,
    expected_revision,
    if_match_revision,
    require_revision,
)
from saber_uli.content.domain.errors import ContentValidationError
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.shared.api.problems import ProblemException, install_problem_handlers


def test_el_etag_es_la_revision_entre_comillas() -> None:
    assert etag(7) == '"7"'


@pytest.mark.parametrize(("header", "expected"), [('"7"', 7), ('W/"7"', 7), (' "12" ', 12)])
def test_lee_if_match_fuerte_o_debil(header: str, expected: int) -> None:
    assert expected_revision(header) == expected


def test_sin_if_match_es_428() -> None:
    with pytest.raises(ProblemException) as error:
        expected_revision(None)

    assert (error.value.status, error.value.slug) == (428, "precondition-required")


@pytest.mark.parametrize("header", ["7", '"siete"', "*", '"1", "2"'])
def test_un_if_match_que_no_es_una_revision_es_un_conflicto(header: str) -> None:
    with pytest.raises(ProblemException) as error:
        expected_revision(header)

    assert (error.value.status, error.value.slug) == (412, "edit-conflict")


def test_un_conflicto_lleva_el_recurso_actual_y_su_etag() -> None:
    problem = edit_conflict({"code": "LC-0001", "revision": 8}, revision=8)

    assert (problem.status, problem.slug) == (412, "edit-conflict")
    assert problem.extensions == {"current": {"code": "LC-0001", "revision": 8}, "etag": '"8"'}


def test_require_revision_compara_con_la_actual() -> None:
    require_revision('"3"', 3)
    with pytest.raises(ProblemException) as error:
        require_revision('"2"', 3, current=lambda: {"revision": 3})

    assert error.value.extensions == {"current": {"revision": 3}, "etag": '"3"'}


@pytest.fixture
def client() -> httpx.AsyncClient:
    app = FastAPI()
    install_problem_handlers(app)

    @app.put("/recurso")
    async def put(revision: Annotated[int, Depends(if_match_revision)]) -> dict[str, int]:
        if revision != 3:
            raise edit_conflict({"revision": 3}, revision=3)
        return {"revision": 4}

    @app.post("/validar")
    async def validate() -> None:
        raise ContentValidationError(
            [ContentIssue("options", ValidationRule.SINGLE_CORRECT_OPTION, "Marca una correcta.")]
        )

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_las_respuestas_http(client: httpx.AsyncClient) -> None:
    async with client:
        missing = await client.put("/recurso")
        stale = await client.put("/recurso", headers={"If-Match": '"2"'})
        fresh = await client.put("/recurso", headers={"If-Match": 'W/"3"'})
        invalid = await client.post("/validar")

    assert missing.status_code == 428
    assert missing.json()["type"] == "urn:saber-uli:problem:precondition-required"
    assert stale.status_code == 412
    assert stale.json()["current"] == {"revision": 3}
    assert stale.json()["etag"] == '"3"'
    assert fresh.status_code == 200
    assert invalid.status_code == 422
    assert invalid.json()["errors"] == [
        {"field": "options", "message": "Marca una correcta.", "rule": "single_correct_option"}
    ]
