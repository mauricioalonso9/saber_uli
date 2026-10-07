"""Dobles en memoria de los puertos de `identity` para pruebas unitarias de casos de uso.

Imitan el comportamiento observable de los repositorios reales (ids asignados al guardar,
búsqueda por identidad institucional) sin base de datos. La unidad de trabajo falsa registra si
se confirmó y descarta lo pendiente al revertir.
"""

from datetime import datetime
from uuid import UUID, uuid4

from saber_uli.identity.application.audit import AuditEntry
from saber_uli.identity.application.ports import AuditRepository, GuestAccessStatus
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.consent import ConsentRecord
from saber_uli.identity.domain.session import RefreshToken, RevocationReason, Session
from saber_uli.identity.domain.user import InstitutionalIdentity, User
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
        return []


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


class FakeConsents:
    async def latest_for_user(self, user_id: UUID) -> ConsentRecord | None:
        return None

    async def current_policy_version_id(self, *, now: datetime) -> UUID | None:
        return None


class FakeIdentityUnitOfWork(IdentityUnitOfWork):
    """Comparte los repositorios entre aperturas (como una base de datos) y cuenta los commits."""

    def __init__(self) -> None:
        super().__init__(EventBus())
        self._users = FakeUsers()
        self._audit = FakeAudit()
        self._sessions = FakeSessions()
        self._guest_access = FakeGuestAccess()
        self._consents = FakeConsents()
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
    def audit(self) -> FakeAudit:
        return self._audit

    async def _commit(self) -> None:
        self.commits += 1

    async def _rollback(self) -> None: ...
