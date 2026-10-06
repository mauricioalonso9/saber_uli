"""Unidad de trabajo del contexto `identity`: transacción más sus repositorios."""

from abc import abstractmethod

from saber_uli.identity.application.ports import (
    AuditRepository,
    ConsentReader,
    GuestAccessReader,
    SessionRepository,
    UserRepository,
)
from saber_uli.shared.application.unit_of_work import UnitOfWork


class IdentityUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def users(self) -> UserRepository: ...

    @property
    @abstractmethod
    def sessions(self) -> SessionRepository: ...

    @property
    @abstractmethod
    def guest_access(self) -> GuestAccessReader: ...

    @property
    @abstractmethod
    def consents(self) -> ConsentReader: ...

    @property
    @abstractmethod
    def audit(self) -> AuditRepository: ...
