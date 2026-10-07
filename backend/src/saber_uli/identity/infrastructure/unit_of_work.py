"""Unidad de trabajo de `identity` sobre SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from saber_uli.identity.application.ports import (
    AuditRepository,
    ConsentRepository,
    GuestAccessReader,
    PolicyRepository,
    SessionRepository,
    UserRepository,
)
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.infrastructure.repositories.audit import SqlAlchemyAuditRepository
from saber_uli.identity.infrastructure.repositories.consents import SqlAlchemyConsentRepository
from saber_uli.identity.infrastructure.repositories.guest_access import (
    SqlAlchemyGuestAccessReader,
)
from saber_uli.identity.infrastructure.repositories.policies import SqlAlchemyPolicyRepository
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
    def consents(self) -> ConsentRepository:
        return SqlAlchemyConsentRepository(self.session)

    @property
    def policies(self) -> PolicyRepository:
        return SqlAlchemyPolicyRepository(self.session)

    @property
    def audit(self) -> AuditRepository:
        return SqlAlchemyAuditRepository(self.session)
