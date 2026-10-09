"""Paginación de listas (contrato: parámetros `Page` y `PageSize`, esquema `PageMeta`)."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Generic, Self, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    """Dependencia de FastAPI para `?page=&page_size=`."""
    return PageParams(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic resuelve mejor los genéricos clásicos
    """Una página de resultados: `items` más `PageMeta` (`page`, `page_size`, `total`).

    Una página más allá del total devuelve `items` vacío, no 404.
    """

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=MAX_PAGE_SIZE)
    total: int = Field(ge=0)

    @classmethod
    def of(cls, items: Iterable[T], params: PageParams, total: int) -> Self:
        return cls(items=list(items), page=params.page, page_size=params.page_size, total=total)
