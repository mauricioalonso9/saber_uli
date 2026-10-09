"""Errores de dominio.

El dominio no conoce HTTP: cada error tiene un `slug` (el mismo del `type` del contrato,
`urn:saber-uli:problem:<slug>`) y pertenece a una categoría que la capa API traduce a un estado
(T021): `UnauthenticatedError` → 401, `NotFoundError` → 404, `PermissionDeniedError` → 403,
`ConflictError` → 409 y `RuleViolationError` → 422. Cada regla define su subclase con su propio
slug, por ejemplo `class LastAdminError(ConflictError): slug = "last-admin"`.

El mensaje va en español y nunca lleva datos personales.
"""

import re
from typing import Any, ClassVar

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class DomainError(Exception):
    slug: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        slug = getattr(cls, "slug", None)
        if not isinstance(slug, str) or not _SLUG.fullmatch(slug):
            raise TypeError(f"{cls.__name__}.slug debe tener formato kebab-case, como 'last-admin'")

    def __init__(self, message: str) -> None:
        if type(self) is DomainError:
            raise TypeError("DomainError es abstracta: use una de sus categorías o una subclase")
        super().__init__(message)
        self.message = message


class UnauthenticatedError(DomainError):
    """Sin sesión válida (sesión vencida, revocada, cuenta desactivada…)."""

    slug = "unauthenticated"


class NotFoundError(DomainError):
    slug = "not-found"


class PermissionDeniedError(DomainError):
    slug = "forbidden"


class ConflictError(DomainError):
    slug = "conflict"


class RuleViolationError(DomainError):
    slug = "validation-error"
