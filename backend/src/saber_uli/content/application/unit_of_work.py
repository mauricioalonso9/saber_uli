"""Unidad de trabajo del contexto `content`: transacción más sus repositorios."""

from abc import abstractmethod

from saber_uli.content.application.ports import (
    ContextRepository,
    ImportRepository,
    ItemRepository,
    MediaRepository,
    ModuleRepository,
    RubricRepository,
    SeedLoadRepository,
    TaxonomyRepository,
)
from saber_uli.shared.application.unit_of_work import UnitOfWork


class ContentUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def modules(self) -> ModuleRepository: ...

    @property
    @abstractmethod
    def taxonomy(self) -> TaxonomyRepository: ...

    @property
    @abstractmethod
    def rubrics(self) -> RubricRepository: ...

    @property
    @abstractmethod
    def contexts(self) -> ContextRepository: ...

    @property
    @abstractmethod
    def items(self) -> ItemRepository: ...

    @property
    @abstractmethod
    def media(self) -> MediaRepository: ...

    @property
    @abstractmethod
    def imports(self) -> ImportRepository: ...

    @property
    @abstractmethod
    def seed_loads(self) -> SeedLoadRepository: ...

    @abstractmethod
    async def lock_seed(self) -> None:
        """Bloqueo de la transacción para la carga del banco inicial (research R-07)."""
        ...
