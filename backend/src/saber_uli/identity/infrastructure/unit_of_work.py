"""Unidad de trabajo de `identity` sobre SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from saber_uli.identity.application.ports import (
    ConsentReader,
    GuestAccessReader,
    SessionRepository,
    UserRepository,
)
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.infrastructure.repositories.consents import SqlAlchemyConsentReader
from saber_uli.identity.infrastructure.repositories.guest_access import (
    SqlAlchemyGuestAccessReader,
)
from saber_uli.identity.infrastructure.repositories.sessions import SqlAlchemySessionRepository
from saber_uli.identity.infrastructure.repositories.users import SqlAlchemyUserRepository
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import SqlAlchemyUnitOfWork


class SqlAlchemyIdentityUnitOfWork(SqlAlchemyUnitOfWork, IdentityUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> None:
        super().__init__(session_factory, bus)

    @property
    def users(self) -> UserRepository:
        return SqlAlchemyUserRepository(self.session)

    @property
    def sessions(self) -> SessionRepository:
        return SqlAlchemySessionRepository(self.session)

    @property
    def guest_access(self) -> GuestAccessReader:
        return SqlAlchemyGuestAccessReader(self.session)

    @property
    def consents(self) -> ConsentReader:
        return SqlAlchemyConsentReader(self.session)
