"""Unidad de trabajo de `content` sobre SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from saber_uli.content.application.ports import (
    ContextRepository,
    ItemRepository,
    MediaRepository,
    ModuleRepository,
    RubricRepository,
    TaxonomyRepository,
)
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.infrastructure.repositories.catalog import (
    SqlAlchemyModuleRepository,
    SqlAlchemyRubricRepository,
    SqlAlchemyTaxonomyRepository,
)
from saber_uli.content.infrastructure.repositories.contexts import (
    SqlAlchemyContextRepository,
    SqlAlchemyMediaRepository,
)
from saber_uli.content.infrastructure.repositories.items import SqlAlchemyItemRepository
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import SqlAlchemyUnitOfWork


class SqlAlchemyContentUnitOfWork(SqlAlchemyUnitOfWork, ContentUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> None:
        super().__init__(session_factory, bus)

    @property
    def modules(self) -> ModuleRepository:
        return SqlAlchemyModuleRepository(self.session)

    @property
    def taxonomy(self) -> TaxonomyRepository:
        return SqlAlchemyTaxonomyRepository(self.session)

    @property
    def rubrics(self) -> RubricRepository:
        return SqlAlchemyRubricRepository(self.session)

    @property
    def contexts(self) -> ContextRepository:
        return SqlAlchemyContextRepository(self.session)

    @property
    def items(self) -> ItemRepository:
        return SqlAlchemyItemRepository(self.session)

    @property
    def media(self) -> MediaRepository:
        return SqlAlchemyMediaRepository(self.session)
