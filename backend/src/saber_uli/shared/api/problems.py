"""Errores como Problem Details (RFC 9457; contrato: esquema `Problem`).

Traduce las categorías de error de dominio a estados HTTP, los errores de validación a 422 con
`errors` por campo en español y cualquier otro error a `about:blank`. Ninguna respuesta repite el
valor recibido ni el texto de una excepción no controlada: pueden contener datos personales.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import iter_route_contexts
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import compile_path

from saber_uli.shared.domain.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
    UnauthenticatedError,
)

PROBLEM_TYPE_PREFIX = "urn:saber-uli:problem:"
PROBLEM_MEDIA_TYPE = "application/problem+json"
ABOUT_BLANK = "about:blank"

_CATEGORY_STATUS: Mapping[type[DomainError], int] = {
    UnauthenticatedError: 401,
    NotFoundError: 404,
    PermissionDeniedError: 403,
    ConflictError: 409,
    RuleViolationError: 422,
}

# Excepciones puntuales por slug (por ejemplo, T123: "batch-too-large" → 413).
STATUS_BY_SLUG: dict[str, int] = {
    # Enlace de invitado inválido, usado o vencido (contrato: `createGuestSession`).
    "access-link-invalid": 400,
    # Lote de invitaciones con más de 500 filas (contrato: `validateInvitationBatch`).
    "batch-too-large": 413,
}

_TITLES: Mapping[int, str] = {
    400: "Solicitud inválida",
    401: "No autenticado",
    403: "Acción no permitida",
    404: "No encontrado",
    405: "Método no permitido",
    409: "Conflicto con el estado actual",
    413: "Contenido demasiado grande",
    415: "Tipo de contenido no admitido",
    422: "Datos inválidos",
    429: "Demasiadas solicitudes",
    500: "Error interno",
    503: "Servicio no disponible",
}

_VALIDATION_DETAIL = "Revisa los datos marcados."

# Mensajes por tipo de error de Pydantic; solo usan `ctx`, nunca el valor recibido.
_FIELD_MESSAGES: Mapping[str, str] = {
    "missing": "Este campo es obligatorio.",
    "string_type": "Debe ser texto.",
    "string_too_short": "Debe tener al menos {min_length} caracteres.",
    "string_too_long": "Debe tener como máximo {max_length} caracteres.",
    "string_pattern_mismatch": "No tiene el formato esperado.",
    "int_parsing": "Debe ser un número entero.",
    "int_type": "Debe ser un número entero.",
    "int_from_float": "Debe ser un número entero.",
    "bool_parsing": "Debe ser verdadero o falso.",
    "bool_type": "Debe ser verdadero o falso.",
    "greater_than": "Debe ser mayor que {gt}.",
    "greater_than_equal": "Debe ser mayor o igual que {ge}.",
    "less_than": "Debe ser menor que {lt}.",
    "less_than_equal": "Debe ser menor o igual que {le}.",
    "uuid_parsing": "Debe ser un identificador UUID válido.",
    "uuid_type": "Debe ser un identificador UUID válido.",
    "enum": "Debe ser uno de los valores permitidos: {expected}.",
    "literal_error": "Debe ser uno de los valores permitidos: {expected}.",
    "date_parsing": "Debe ser una fecha con formato AAAA-MM-DD.",
    "date_type": "Debe ser una fecha con formato AAAA-MM-DD.",
    "date_from_datetime_parsing": "Debe ser una fecha con formato AAAA-MM-DD.",
    "datetime_parsing": "Debe ser una fecha y hora válida.",
    "datetime_type": "Debe ser una fecha y hora válida.",
    "list_type": "Debe ser una lista.",
    "too_short": "Debe tener al menos {min_length} elementos.",
    "too_long": "Debe tener como máximo {max_length} elementos.",
    "model_type": "Debe ser un objeto.",
    "dict_type": "Debe ser un objeto.",
    "json_invalid": "El cuerpo no es un JSON válido.",
    "value_error": "Valor inválido.",
}
_DEFAULT_FIELD_MESSAGE = "Valor inválido."
_LOCATIONS = frozenset({"body", "query", "path", "header", "cookie"})

_log = structlog.get_logger(__name__)


class FieldError(BaseModel):
    field: str
    message: str


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[FieldError] | None = None


class ProblemException(Exception):
    """Problema propio de la capa API (`unauthenticated`, `consent-required`, `rate-limited`…)."""

    def __init__(
        self,
        status: int,
        slug: str,
        *,
        detail: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(slug)
        self.status = status
        self.slug = slug
        self.detail = detail
        self.headers = dict(headers or {})


def _title(status: int) -> str:
    return _TITLES.get(status) or HTTPStatus(status).phrase


def problem_response(
    request: Request,
    status: int,
    type_: str,
    *,
    detail: str | None = None,
    errors: list[FieldError] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    problem = Problem(
        type=type_,
        title=_title(status),
        status=status,
        detail=detail,
        instance=request.url.path,  # sin la consulta: podría llevar datos personales
        errors=errors,
    )
    return JSONResponse(
        problem.model_dump(mode="json", exclude_none=True),
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=dict(headers) if headers else None,
    )


def _domain_status(error: DomainError) -> int:
    if error.slug in STATUS_BY_SLUG:
        return STATUS_BY_SLUG[error.slug]
    for klass in type(error).__mro__:
        if klass in _CATEGORY_STATUS:
            return _CATEGORY_STATUS[klass]
    return 500  # pragma: no cover - toda subclase concreta pertenece a una categoría


def _field_error(error: Mapping[str, Any]) -> FieldError:
    loc = [str(part) for part in error.get("loc", ())]
    if loc and loc[0] in _LOCATIONS:
        loc = loc[1:]
    if error.get("type") == "json_invalid":
        loc = ["body"]
    template = _FIELD_MESSAGES.get(str(error.get("type")), _DEFAULT_FIELD_MESSAGE)
    try:
        message = template.format(**(error.get("ctx") or {}))
    except (KeyError, IndexError):
        message = _DEFAULT_FIELD_MESSAGE
    return FieldError(field=".".join(loc) or "body", message=message)


async def _on_domain_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, DomainError):  # Starlette tipa los manejadores con Exception
        raise exc
    return problem_response(
        request, _domain_status(exc), f"{PROBLEM_TYPE_PREFIX}{exc.slug}", detail=exc.message
    )


async def _on_problem(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ProblemException):  # Starlette tipa los manejadores con Exception
        raise exc
    return problem_response(
        request,
        exc.status,
        f"{PROBLEM_TYPE_PREFIX}{exc.slug}",
        detail=exc.detail,
        headers=exc.headers,
    )


async def _on_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # Starlette tipa los manejadores con Exception
        raise exc
    errors = exc.errors()
    if errors and all(tuple(error.get("loc", ()))[:1] == ("path",) for error in errors):
        # Un identificador mal formado en la ruta no nombra ningún recurso: 404, como uno que no
        # existe (el contrato no documenta 422 para los parámetros de ruta).
        return problem_response(request, 404, f"{PROBLEM_TYPE_PREFIX}not-found")
    return problem_response(
        request,
        422,
        f"{PROBLEM_TYPE_PREFIX}validation-error",
        detail=_VALIDATION_DETAIL,
        errors=[_field_error(error) for error in errors],
    )


def _allowed_methods(request: Request) -> str | None:
    """Métodos de todas las rutas con esta URL.

    Starlette responde 405 con el `Allow` de la primera ruta que coincide, aunque otra ruta con la
    misma URL atienda otro método (por ejemplo, `GET` y `POST` en `/api/v1/me/consents`).
    """
    path = request.url.path
    methods: set[str] = set()
    for route in iter_route_contexts(request.app.router.routes):
        if route.methods and route.path_format:
            regex, _, _ = compile_path(route.path_format)
            if regex.match(path):
                methods |= route.methods
    return ", ".join(sorted(methods)) or None


async def _on_http_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # Starlette tipa los manejadores con Exception
        raise exc
    if exc.status_code == 400:
        # FastAPI responde 400 cuando el cuerpo no se puede leer (por ejemplo, bytes que no son
        # UTF-8); para el contrato es un dato inválido más.
        return problem_response(
            request,
            422,
            f"{PROBLEM_TYPE_PREFIX}validation-error",
            detail=_VALIDATION_DETAIL,
            errors=[_field_error({"type": "json_invalid"})],
        )
    headers = dict(exc.headers or {})
    if exc.status_code == 405 and (allowed := _allowed_methods(request)):
        headers["Allow"] = allowed
    type_ = f"{PROBLEM_TYPE_PREFIX}not-found" if exc.status_code == 404 else ABOUT_BLANK
    return problem_response(request, exc.status_code, type_, headers=headers or None)


async def _on_unhandled(request: Request, exc: Exception) -> JSONResponse:
    _log.exception("unhandled_error", path=request.url.path, error_type=type(exc).__name__)
    return problem_response(request, 500, ABOUT_BLANK)


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _on_domain_error)
    app.add_exception_handler(ProblemException, _on_problem)
    app.add_exception_handler(RequestValidationError, _on_validation_error)
    app.add_exception_handler(StarletteHTTPException, _on_http_error)
    app.add_exception_handler(Exception, _on_unhandled)
