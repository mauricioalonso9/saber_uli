"""Unidad de trabajo de `content` sobre SQLAlchemy."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from saber_uli.content.application.ports import (
    ContextRepository,
    ExportRepository,
    ImportRepository,
    ItemRepository,
    MediaRepository,
    ModuleRepository,
    RubricRepository,
    SeedLoadRepository,
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
from saber_uli.content.infrastructure.repositories.exports import SqlAlchemyExportRepository
from saber_uli.content.infrastructure.repositories.imports import SqlAlchemyImportRepository
from saber_uli.content.infrastructure.repositories.items import SqlAlchemyItemRepository
from saber_uli.content.infrastructure.repositories.seed_loads import SqlAlchemySeedLoadRepository
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import SqlAlchemyUnitOfWork

# Clave del advisory lock de la carga del banco inicial ("SEED" en ASCII).
SEED_LOCK_KEY = 0x53454544


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

    @property
    def imports(self) -> ImportRepository:
        return SqlAlchemyImportRepository(self.session)

    @property
    def exports(self) -> ExportRepository:
        return SqlAlchemyExportRepository(self.session)

    @property
    def seed_loads(self) -> SeedLoadRepository:
        return SqlAlchemySeedLoadRepository(self.session)

    async def lock_seed(self) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK_KEY}
        )
