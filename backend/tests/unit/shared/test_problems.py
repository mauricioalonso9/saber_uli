"""T020: Problem Details (RFC 9457) y paginación (contrato: Problem, PageMeta, Page, PageSize)."""

from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError

from saber_uli.shared.api import problems
from saber_uli.shared.api.pagination import Page, PageParams, page_params
from saber_uli.shared.api.problems import (
    PROBLEM_MEDIA_TYPE,
    PROBLEM_TYPE_PREFIX,
    ProblemException,
    install_problem_handlers,
)
from saber_uli.shared.domain.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
    UnauthenticatedError,
)


class _SesionVencida(UnauthenticatedError):
    slug = "session-expired"


class _GrupoInexistente(NotFoundError):
    slug = "group-not-found"


class _SinPermiso(PermissionDeniedError):
    slug = "not-a-teacher"


class _UltimoAdmin(ConflictError):
    slug = "last-admin"


class _CorreoInstitucional(RuleViolationError):
    slug = "institutional-email-not-invitable"


class _LoteGrande(RuleViolationError):
    slug = "batch-too-large"


ERRORS = {
    "unauthenticated": _SesionVencida("Tu sesión venció."),
    "not-found": _GrupoInexistente("El grupo no existe."),
    "forbidden": _SinPermiso("La persona no es docente."),
    "conflict": _UltimoAdmin("No puedes quitar el último administrador."),
    "rule": _CorreoInstitucional("Los correos institucionales no se invitan."),
    "batch": _LoteGrande("El lote es demasiado grande."),
}


class Persona(BaseModel):
    email: str
    edad: int = Field(ge=0)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    install_problem_handlers(app)

    @app.get("/boom/{kind}")
    def boom(kind: str) -> None:
        raise ERRORS[kind]

    @app.get("/limitado")
    def limitado() -> None:
        raise ProblemException(
            429, "rate-limited", detail="Intenta más tarde.", headers={"Retry-After": "30"}
        )

    @app.post("/personas")
    def personas(persona: Persona) -> Persona:
        return persona

    @app.get("/lista")
    def lista(params: Annotated[PageParams, Depends(page_params)]) -> Page[int]:
        total = 60
        items = list(range(params.offset, min(params.offset + params.limit, total)))
        return Page.of(items, params, total)

    @app.get("/falla")
    def falla() -> None:
        raise RuntimeError("fallo con ana@unilibre.edu.co")

    return TestClient(app, raise_server_exceptions=False)


def assert_problem(response: Any, status: int, type_: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body: dict[str, Any] = response.json()
    assert body["type"] == type_
    assert body["status"] == status
    assert body["title"]
    assert None not in body.values()
    return body


# --- Errores de dominio --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "status", "slug", "title"),
    [
        ("unauthenticated", 401, "session-expired", "No autenticado"),
        ("not-found", 404, "group-not-found", "No encontrado"),
        ("forbidden", 403, "not-a-teacher", "Acción no permitida"),
        ("conflict", 409, "last-admin", "Conflicto con el estado actual"),
        ("rule", 422, "institutional-email-not-invitable", "Datos inválidos"),
    ],
)
def test_categorias_de_dominio(
    client: TestClient, kind: str, status: int, slug: str, title: str
) -> None:
    body = assert_problem(
        client.get(f"/boom/{kind}?correo=ana@unilibre.edu.co"),
        status,
        f"{PROBLEM_TYPE_PREFIX}{slug}",
    )

    assert body["title"] == title
    assert body["detail"] == ERRORS[kind].message
    assert body["instance"] == f"/boom/{kind}"


def test_status_by_slug_tiene_prioridad(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(problems.STATUS_BY_SLUG, "batch-too-large", 413)

    assert_problem(client.get("/boom/batch"), 413, f"{PROBLEM_TYPE_PREFIX}batch-too-large")


def test_problem_exception_conserva_cabeceras(client: TestClient) -> None:
    response = client.get("/limitado")
    body = assert_problem(response, 429, f"{PROBLEM_TYPE_PREFIX}rate-limited")

    assert response.headers["Retry-After"] == "30"
    assert body["detail"] == "Intenta más tarde."


# --- Validación ----------------------------------------------------------------------------


def test_errores_de_validacion_por_campo_en_espanol(client: TestClient) -> None:
    body = assert_problem(
        client.post("/personas", json={"edad": -1}), 422, f"{PROBLEM_TYPE_PREFIX}validation-error"
    )

    errors = {e["field"]: e["message"] for e in body["errors"]}
    assert set(errors) == {"email", "edad"}
    assert errors["email"] == "Este campo es obligatorio."
    assert errors["edad"] == "Debe ser mayor o igual que 0."


def test_la_validacion_no_repite_el_valor_recibido(client: TestClient) -> None:
    response = client.post("/personas", json={"email": "x", "edad": "ana@unilibre.edu.co"})
    body = assert_problem(response, 422, f"{PROBLEM_TYPE_PREFIX}validation-error")

    assert "ana@unilibre.edu.co" not in response.text
    assert body["errors"] == [{"field": "edad", "message": "Debe ser un número entero."}]


def test_json_invalido(client: TestClient) -> None:
    response = client.post(
        "/personas", content=b"{no es json", headers={"Content-Type": "application/json"}
    )

    assert_problem(response, 422, f"{PROBLEM_TYPE_PREFIX}validation-error")


# --- Paginación ----------------------------------------------------------------------------


def test_paginacion_por_defecto(client: TestClient) -> None:
    body = client.get("/lista").json()

    assert set(body) == {"items", "page", "page_size", "total"}
    assert (body["page"], body["page_size"], body["total"]) == (1, 25, 60)
    assert body["items"] == list(range(25))


def test_offset_de_la_tercera_pagina(client: TestClient) -> None:
    body = client.get("/lista?page=3&page_size=25").json()

    assert body["items"] == list(range(50, 60))
    assert PageParams(page=3, page_size=25).offset == 50
    assert PageParams(page=3, page_size=25).limit == 25


def test_page_size_maximo(client: TestClient) -> None:
    assert client.get("/lista?page_size=100").json()["page_size"] == 100


@pytest.mark.parametrize(("query", "field"), [("page=0", "page"), ("page_size=101", "page_size")])
def test_paginacion_fuera_de_rango(client: TestClient, query: str, field: str) -> None:
    body = assert_problem(
        client.get(f"/lista?{query}"), 422, f"{PROBLEM_TYPE_PREFIX}validation-error"
    )

    assert [e["field"] for e in body["errors"]] == [field]


def test_pagina_mas_alla_del_total(client: TestClient) -> None:
    response = client.get("/lista?page=10")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_total_negativo_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        Page.of([], PageParams(page=1, page_size=25), -1)


# --- Errores HTTP genéricos y no controlados -----------------------------------------------


def test_ruta_inexistente(client: TestClient) -> None:
    assert_problem(client.get("/no-existe"), 404, f"{PROBLEM_TYPE_PREFIX}not-found")


def test_metodo_no_permitido(client: TestClient) -> None:
    assert_problem(client.delete("/lista"), 405, "about:blank")


def test_excepcion_no_controlada_no_filtra_detalles(client: TestClient) -> None:
    response = client.get("/falla")
    body = assert_problem(response, 500, "about:blank")

    assert "detail" not in body
    assert "ana@unilibre.edu.co" not in response.text
    assert "fallo" not in response.text
