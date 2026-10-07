"""Dobles en memoria de los puertos de `identity` para pruebas unitarias de casos de uso.

Imitan el comportamiento observable de los repositorios reales (ids asignados al guardar,
búsqueda por identidad institucional) sin base de datos. La unidad de trabajo falsa registra si
se confirmó y descarta lo pendiente al revertir.
"""

from collections.abc import Collection
from datetime import datetime
from uuid import UUID, uuid4

from saber_uli.identity.application.audit import AuditEntry
from saber_uli.identity.application.ports import AuditRepository, ConsentEntry, GuestAccessStatus
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.access_link import AccessLink, LinkPurpose
from saber_uli.identity.domain.consent import ConsentRecord
from saber_uli.identity.domain.invitation import Invitation, InvitationStatus
from saber_uli.identity.domain.invitation_batch import InvitationBatch
from saber_uli.identity.domain.policy import PolicyVersion
from saber_uli.identity.domain.profile import Profile
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import RefreshToken, RevocationReason, Session
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.domain.user import InstitutionalIdentity, User, UserStatus
from saber_uli.shared.application.event_bus import EventBus


class FakeUsers:
    def __init__(self) -> None:
        self.rows: dict[UUID, User] = {}

    async def add(self, user: User) -> User:
        user.id = uuid4()
        self.rows[user.id] = user
        return user

    async def save(self, user: User) -> None:
        assert user.id in self.rows
        self.rows[user.id] = user

    async def get(self, user_id: UUID) -> User | None:
        return self.rows.get(user_id)

    async def get_by_entra_identity(self, identity: InstitutionalIdentity) -> User | None:
        return next((u for u in self.rows.values() if u.entra_identity == identity), None)

    async def find_active_guest_by_email(self, email: str) -> User | None:
        wanted = email.strip().lower()
        return next(
            (u for u in self.rows.values() if (u.email or "").lower() == wanted),
            None,
        )

    async def lock_active_admins(self) -> list[UUID]:
        return sorted(
            user_id
            for user_id, user in self.rows.items()
            if Role.ADMIN in user.roles and user.status is UserStatus.ACTIVE
        )

    async def search(
        self,
        *,
        q: str | None,
        kind: object,
        role: Role | None,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        items = [
            u
            for u in self.rows.values()
            if (role is None or role in u.roles) and (status is None or u.status.value == status)
        ]
        return items[offset : offset + limit], len(items)

    async def display_names(self, user_ids: Collection[UUID]) -> dict[UUID, str | None]:
        return {i: self.rows[i].display_name for i in user_ids if i in self.rows}


class FakeAudit(AuditRepository):
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    async def add(self, entry: AuditEntry) -> None:
        self.entries.append(entry)


class FakeSessions:
    async def add(self, session: Session) -> Session:
        session.id = uuid4()
        return session

    async def save(self, session: Session) -> None: ...

    async def get(self, session_id: UUID) -> Session | None:
        return None

    async def add_refresh_token(self, token: RefreshToken) -> RefreshToken:
        return token

    async def save_refresh_token(self, token: RefreshToken) -> None: ...

    async def get_refresh_token_for_update(self, token_hash: bytes) -> RefreshToken | None:
        return None

    async def revoke_all_for_user(
        self, user_id: UUID, *, now: datetime, reason: RevocationReason
    ) -> int:
        return 0


class FakeGuestAccess:
    async def status_for(self, user_id: UUID, *, now: datetime) -> GuestAccessStatus:
        return GuestAccessStatus.NONE

    async def expires_at_for(self, user_id: UUID) -> datetime | None:
        return None


class FakeConsents:
    async def latest_for_user(self, user_id: UUID) -> ConsentRecord | None:
        return None

    async def current_policy_version_id(self, *, now: datetime) -> UUID | None:
        return None

    async def history_for_user(self, user_id: UUID) -> list[ConsentEntry]:
        return []

    async def add(self, user_id: UUID, record: ConsentRecord) -> ConsentEntry:
        raise NotImplementedError


class FakePolicies:
    async def current(self, *, now: datetime) -> PolicyVersion | None:
        return None

    async def get(self, version_id: UUID) -> PolicyVersion | None:
        return None

    async def versions(self) -> set[str]:
        return set()

    async def latest_effective_from(self) -> datetime | None:
        return None

    async def add(self, version: PolicyVersion) -> PolicyVersion:
        raise NotImplementedError


class FakeProfiles:
    def __init__(self) -> None:
        self.rows: dict[UUID, Profile] = {}

    async def get(self, user_id: UUID) -> Profile | None:
        return self.rows.get(user_id)

    async def save(self, profile: Profile) -> None:
        self.rows[profile.user_id] = profile


class FakePrograms:
    def __init__(self) -> None:
        self.rows: dict[UUID, Program] = {}

    async def get(self, program_id: UUID) -> Program | None:
        return self.rows.get(program_id)

    async def get_by_code(self, code: str) -> Program | None:
        return next((p for p in self.rows.values() if p.code == code), None)

    async def list_active(self) -> list[Program]:
        return sorted((p for p in self.rows.values() if p.active), key=lambda p: p.name)

    async def add(self, program: Program) -> Program:
        program.id = uuid4()
        self.rows[program.id] = program
        return program

    async def save(self, program: Program) -> None:
        assert program.id is not None
        self.rows[program.id] = program


class FakeInvitations:
    def __init__(self) -> None:
        self.rows: dict[UUID, Invitation] = {}

    async def add(self, invitation: Invitation) -> Invitation:
        invitation.id = uuid4()
        self.rows[invitation.id] = invitation
        return invitation

    async def save(self, invitation: Invitation) -> None:
        assert invitation.id is not None
        self.rows[invitation.id] = invitation

    async def get_for_update(self, invitation_id: UUID) -> Invitation | None:
        return self.rows.get(invitation_id)

    async def get(self, invitation_id: UUID) -> Invitation | None:
        return self.rows.get(invitation_id)

    async def search(
        self,
        *,
        invited_by: UUID | None,
        status: InvitationStatus | None,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Invitation], int]:
        items = [
            i
            for i in self.rows.values()
            if (invited_by is None or i.invited_by == invited_by)
            and (status is None or i.status is status)
            and (not q or q.lower() in (i.email or "").lower())
        ]
        return items[offset : offset + limit], len(items)

    async def active_emails(self, emails: Collection[str]) -> set[str]:
        wanted = {e.lower() for e in emails}
        return {
            (i.email or "").lower()
            for i in self.rows.values()
            if (i.email or "").lower() in wanted
            and i.status in (InvitationStatus.SENT, InvitationStatus.ACCEPTED)
        }

    async def find_active_by_email(self, email: str) -> Invitation | None:
        wanted = email.strip().lower()
        return next(
            (
                i
                for i in self.rows.values()
                if (i.email or "").lower() == wanted
                and i.status in (InvitationStatus.SENT, InvitationStatus.ACCEPTED)
            ),
            None,
        )

    async def set_delivery_status(self, invitation_id: UUID, status: str) -> None:
        return None


class FakeInvitationBatches:
    def __init__(self) -> None:
        self.rows: dict[UUID, InvitationBatch] = {}

    async def add(self, batch: InvitationBatch) -> InvitationBatch:
        batch.id = uuid4()
        self.rows[batch.id] = batch
        return batch

    async def save(self, batch: InvitationBatch) -> None:
        assert batch.id is not None
        self.rows[batch.id] = batch

    async def get(self, batch_id: UUID) -> InvitationBatch | None:
        return self.rows.get(batch_id)

    async def get_for_update(self, batch_id: UUID) -> InvitationBatch | None:
        return self.rows.get(batch_id)


class FakeAccessLinks:
    def __init__(self) -> None:
        self.rows: list[AccessLink] = []

    async def add(self, link: AccessLink) -> AccessLink:
        link.id = uuid4()
        self.rows.append(link)
        return link

    async def save(self, link: AccessLink) -> None:
        return None

    async def get_by_hash_for_update(self, token_hash: bytes) -> AccessLink | None:
        return next((link for link in self.rows if link.token_hash == token_hash), None)

    async def unused_for(self, invitation_id: UUID, purpose: LinkPurpose) -> list[AccessLink]:
        return [
            link
            for link in self.rows
            if link.invitation_id == invitation_id
            and link.purpose is purpose
            and link.used_at is None
        ]


class FakeSettings:
    def __init__(self) -> None:
        self.current = IdentitySettings()

    async def load(self) -> IdentitySettings:
        return self.current


class FakeGroups:
    """Grupos: las pruebas unitarias de grupos usan solo el dominio (T138)."""


class FakeIdentityUnitOfWork(IdentityUnitOfWork):
    """Comparte los repositorios entre aperturas (como una base de datos) y cuenta los commits."""

    def __init__(self) -> None:
        super().__init__(EventBus())
        self._users = FakeUsers()
        self._audit = FakeAudit()
        self._sessions = FakeSessions()
        self._guest_access = FakeGuestAccess()
        self._consents = FakeConsents()
        self._policies = FakePolicies()
        self._profiles = FakeProfiles()
        self._programs = FakePrograms()
        self._groups = FakeGroups()
        self._invitations = FakeInvitations()
        self._invitation_batches = FakeInvitationBatches()
        self._access_links = FakeAccessLinks()
        self._settings = FakeSettings()
        self.commits = 0

    def __call__(self) -> "FakeIdentityUnitOfWork":
        return self

    @property
    def users(self) -> FakeUsers:
        return self._users

    @property
    def sessions(self) -> FakeSessions:
        return self._sessions

    @property
    def guest_access(self) -> FakeGuestAccess:
        return self._guest_access

    @property
    def consents(self) -> FakeConsents:
        return self._consents

    @property
    def policies(self) -> FakePolicies:
        return self._policies

    @property
    def profiles(self) -> FakeProfiles:
        return self._profiles

    @property
    def programs(self) -> FakePrograms:
        return self._programs

    @property
    def groups(self) -> FakeGroups:
        return self._groups

    @property
    def invitations(self) -> FakeInvitations:
        return self._invitations

    @property
    def invitation_batches(self) -> FakeInvitationBatches:
        return self._invitation_batches

    @property
    def access_links(self) -> FakeAccessLinks:
        return self._access_links

    @property
    def settings(self) -> FakeSettings:
        return self._settings

    @property
    def audit(self) -> FakeAudit:
        return self._audit

    async def _commit(self) -> None:
        self.commits += 1

    async def _rollback(self) -> None: ...
