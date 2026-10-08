"""Unidad de trabajo del contexto `identity`: transacción más sus repositorios."""

from abc import abstractmethod

from saber_uli.identity.application.ports import (
    AccessLinkRepository,
    AuditRepository,
    ConsentRepository,
    DeletionRequestRepository,
    GroupRepository,
    GuestAccessReader,
    InvitationBatchRepository,
    InvitationRepository,
    PolicyRepository,
    ProfileRepository,
    ProgramRepository,
    SessionRepository,
    SettingsReader,
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
    def consents(self) -> ConsentRepository: ...

    @property
    @abstractmethod
    def policies(self) -> PolicyRepository: ...

    @property
    @abstractmethod
    def profiles(self) -> ProfileRepository: ...

    @property
    @abstractmethod
    def programs(self) -> ProgramRepository: ...

    @property
    @abstractmethod
    def groups(self) -> GroupRepository: ...

    @property
    @abstractmethod
    def invitations(self) -> InvitationRepository: ...

    @property
    @abstractmethod
    def invitation_batches(self) -> InvitationBatchRepository: ...

    @property
    @abstractmethod
    def access_links(self) -> AccessLinkRepository: ...

    @property
    @abstractmethod
    def settings(self) -> SettingsReader: ...

    @property
    @abstractmethod
    def audit(self) -> AuditRepository: ...

    @property
    @abstractmethod
    def deletion_requests(self) -> DeletionRequestRepository: ...
