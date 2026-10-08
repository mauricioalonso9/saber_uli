"""Puertos de la capa de aplicación de `identity` (los implementa `identity.infrastructure`)."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from saber_uli.identity.domain.access_link import AccessLink, LinkPurpose
from saber_uli.identity.domain.consent import ConsentDecision, ConsentRecord
from saber_uli.identity.domain.deletion_request import DeletionRequest, DeletionStatus
from saber_uli.identity.domain.group import Group
from saber_uli.identity.domain.invitation import Invitation, InvitationStatus
from saber_uli.identity.domain.invitation_batch import InvitationBatch
from saber_uli.identity.domain.policy import PolicyVersion
from saber_uli.identity.domain.profile import Profile
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import RefreshToken, RevocationReason, Session
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.domain.user import InstitutionalIdentity, User, UserKind

if TYPE_CHECKING:
    from saber_uli.identity.application.audit import AuditEntry

ACCESS_TOKEN_TTL_SECONDS = 600


@dataclass(frozen=True)
class AccessTokenClaims:
    """Contenido del token de acceso (R-14)."""

    sub: UUID
    sid: UUID
    roles: tuple[str, ...]
    epoch: int
    priv: bool
    iat: datetime

    @property
    def expires_at(self) -> datetime:
        return self.iat + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)


class AccessTokenEncoder(Protocol):
    def encode(self, claims: AccessTokenClaims) -> str: ...


class RefreshTokenGenerator(Protocol):
    def new(self) -> tuple[str, bytes]:
        """Token en claro (solo para la cookie) y su hash (solo para la base de datos)."""
        ...

    def hash(self, plaintext: str) -> bytes: ...


class AccessTokenDecoder(Protocol):
    def decode(self, token: str, *, now: datetime) -> AccessTokenClaims:
        """Lanza un `UnauthenticatedError` si el token no es válido o venció."""
        ...


class EpochStore(Protocol):
    """Caché de `auth_epoch` por usuario (R-16). Nunca lanza: si falla, se comporta como vacía."""

    async def get(self, user_id: UUID) -> int | None: ...

    async def set(self, user_id: UUID, epoch: int) -> None: ...

    async def invalidate(self, user_id: UUID) -> None: ...


class SessionRevocations(Protocol):
    """Sesiones revocadas cuyo token de acceso aún no vence (ASVS V3.3.1). Nunca lanza."""

    async def revoke(self, session_id: UUID) -> None: ...

    async def is_revoked(self, session_id: UUID) -> bool: ...


class GuestAccessStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    NONE = "none"


class GuestAccessReader(Protocol):
    async def status_for(self, user_id: UUID, *, now: datetime) -> GuestAccessStatus:
        """Estado del acceso derivado de la invitación más reciente del invitado (§4.2)."""
        ...

    async def expires_at_for(self, user_id: UUID) -> datetime | None:
        """Vencimiento del acceso según la invitación más reciente (`None` si no hay)."""
        ...


@dataclass(frozen=True)
class AuditRecord:
    """Evento de auditoría guardado (esquema `AuditEvent`)."""

    id: UUID
    occurred_at: datetime
    actor_id: UUID | None
    action: str
    target_type: str
    target_id: UUID | None
    subject_user_id: UUID | None
    details: dict[str, Any]


class AuditRepository(Protocol):
    async def add(self, entry: "AuditEntry") -> None: ...

    async def search(
        self,
        *,
        action: str | None,
        actor_id: UUID | None,
        subject_user_id: UUID | None,
        since: datetime | None,
        until: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AuditRecord], int]:
        """Eventos del más reciente al más antiguo (FR-035, solo lectura)."""
        ...


@dataclass(frozen=True)
class ConsentEntry:
    """Registro guardado de una decisión, con la versión de la política (esquema `Consent`)."""

    id: UUID
    policy_version_id: UUID
    policy_version: str
    decision: ConsentDecision
    channel: str
    decided_at: datetime


class ConsentRepository(Protocol):
    """Autorizaciones de datos: solo inserción y lectura (data-model §2.11)."""

    async def latest_for_user(self, user_id: UUID) -> ConsentRecord | None: ...

    async def current_policy_version_id(self, *, now: datetime) -> UUID | None: ...

    async def history_for_user(self, user_id: UUID) -> list[ConsentEntry]:
        """Decisiones del usuario, de la más reciente a la más antigua."""
        ...

    async def add(self, user_id: UUID, record: ConsentRecord) -> ConsentEntry: ...


class ProfileRepository(Protocol):
    async def get(self, user_id: UUID) -> Profile | None: ...

    async def save(self, profile: Profile) -> None:
        """Inserta o actualiza el perfil (uno por usuario)."""
        ...


class ProgramRepository(Protocol):
    async def get(self, program_id: UUID) -> Program | None: ...

    async def get_by_code(self, code: str) -> Program | None: ...

    async def list_active(self) -> list[Program]:
        """Programas activos ordenados por nombre y seccional."""
        ...

    async def search(
        self, *, q: str | None, offset: int, limit: int
    ) -> tuple[list[Program], int]: ...

    async def add(self, program: Program) -> Program:
        """Lanza `ProgramCodeExistsError` si el código ya existe."""
        ...

    async def save(self, program: Program) -> None: ...


class InvitationRepository(Protocol):
    async def add(self, invitation: Invitation) -> Invitation:
        """Guarda y asigna el `id`. Lanza `InvitationAlreadyActiveError` si el correo ya tiene
        una invitación vigente (`sent` o `accepted`)."""
        ...

    async def save(self, invitation: Invitation) -> None: ...

    async def get_for_update(self, invitation_id: UUID) -> Invitation | None: ...

    async def get(self, invitation_id: UUID) -> Invitation | None: ...

    async def search(
        self,
        *,
        invited_by: UUID | None,
        status: InvitationStatus | None,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Invitation], int]:
        """Página de invitaciones (las más recientes primero) y el total."""
        ...

    async def active_emails(self, emails: Collection[str]) -> set[str]:
        """De `emails`, los que ya tienen invitación vigente (en minúsculas)."""
        ...

    async def find_active_by_email(self, email: str) -> Invitation | None:
        """Invitación `sent` o `accepted` del correo, sin distinguir mayúsculas."""
        ...

    async def set_delivery_status(self, invitation_id: UUID, status: str) -> None:
        """`queued`, `sent` o `failed` (caso límite de rebote)."""
        ...


@dataclass(frozen=True)
class PersonName:
    """Identificador y nombre visible (sin correo: vista del docente, FR-027)."""

    user_id: UUID
    display_name: str | None


@dataclass(frozen=True)
class MemberContact:
    """Miembro de un grupo visto por el administrador (incluye el correo)."""

    user_id: UUID
    display_name: str | None
    email: str | None


class GroupRepository(Protocol):
    async def add(self, group: Group) -> Group: ...

    async def save(self, group: Group) -> None: ...

    async def get(self, group_id: UUID) -> Group | None: ...

    async def search(
        self, *, q: str | None, offset: int, limit: int
    ) -> tuple[list[Group], int]: ...

    async def member_count(self, group_id: UUID) -> int: ...

    async def teachers(self, group_id: UUID) -> list[PersonName]: ...

    async def add_members(self, group_id: UUID, user_ids: Collection[UUID]) -> list[UUID]:
        """Agrega los que aún no son miembros y los devuelve."""
        ...

    async def remove_member(self, group_id: UUID, user_id: UUID) -> bool: ...

    async def add_teachers(self, group_id: UUID, user_ids: Collection[UUID]) -> list[UUID]: ...

    async def remove_teacher(self, group_id: UUID, user_id: UUID) -> bool: ...

    async def teaching_groups(self, user_id: UUID) -> list[Group]:
        """Grupos sin archivar donde el usuario es docente."""
        ...

    async def is_teacher(self, group_id: UUID, user_id: UUID) -> bool: ...

    async def students(
        self, group_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[PersonName], int]: ...

    async def members(
        self, group_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[MemberContact], int]: ...


class InvitationBatchRepository(Protocol):
    async def add(self, batch: InvitationBatch) -> InvitationBatch: ...

    async def save(self, batch: InvitationBatch) -> None: ...

    async def get(self, batch_id: UUID) -> InvitationBatch | None: ...

    async def get_for_update(self, batch_id: UUID) -> InvitationBatch | None: ...


class AccessLinkRepository(Protocol):
    async def add(self, link: AccessLink) -> AccessLink: ...

    async def save(self, link: AccessLink) -> None: ...

    async def get_by_hash_for_update(self, token_hash: bytes) -> AccessLink | None:
        """Enlace bloqueado hasta el fin de la transacción (un solo uso aunque lleguen dos)."""
        ...

    async def unused_for(self, invitation_id: UUID, purpose: LinkPurpose) -> list[AccessLink]: ...


class SettingsReader(Protocol):
    async def load(self) -> IdentitySettings: ...

    async def save(
        self, settings: IdentitySettings, *, previous: IdentitySettings, updated_by: UUID | None
    ) -> None: ...


class LinkTokenGenerator(Protocol):
    def new(self) -> tuple[str, bytes]:
        """Token en claro (solo para el correo) y su hash."""
        ...

    def hash(self, plaintext: str) -> bytes: ...


class PolicyRepository(Protocol):
    """Versiones de la política: solo inserción y lectura (data-model §2.10)."""

    async def current(self, *, now: datetime) -> PolicyVersion | None:
        """La de mayor `effective_from ≤ now`."""
        ...

    async def get(self, version_id: UUID) -> PolicyVersion | None: ...

    async def versions(self) -> set[str]: ...

    async def latest_effective_from(self) -> datetime | None:
        """Mayor `effective_from` entre todas las versiones, incluidas las programadas."""
        ...

    async def add(self, version: PolicyVersion) -> PolicyVersion:
        """Guarda la versión y la devuelve con su `id`.

        Lanza `PolicyVersionExistsError` si otra transacción publicó la misma versión.
        """
        ...


class UserAlreadyExistsError(Exception):
    """Otra transacción ya creó la cuenta con la misma identidad institucional."""


class UserRepository(Protocol):
    async def add(self, user: User) -> User:
        """Guarda un usuario nuevo y le asigna el `id` generado por la base de datos.

        Lanza `UserAlreadyExistsError` si la identidad (`tid`, `oid`) ya existe.
        """
        ...

    async def save(self, user: User) -> None:
        """Persiste los cambios de un usuario existente (estado, época, datos y roles)."""
        ...

    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_entra_identity(self, identity: InstitutionalIdentity) -> User | None: ...

    async def find_by_email(self, email: str) -> User | None:
        """Cuenta no suprimida con ese correo, sin distinguir mayúsculas."""
        ...

    async def find_active_guest_by_email(self, email: str) -> User | None:
        """Invitado no suprimido con ese correo, sin distinguir mayúsculas."""
        ...

    async def lock_active_admins(self) -> list[UUID]:
        """Bloquea (`FOR UPDATE`) y devuelve los administradores activos (FR-025, FR-034d)."""
        ...

    async def search(
        self,
        *,
        q: str | None,
        kind: UserKind | None,
        role: Role | None,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        """Página de cuentas (las más recientes primero). `status` admite los estados visibles
        (`guest_expired` y `guest_revoked` se derivan de la invitación)."""
        ...

    async def display_names(self, user_ids: Collection[UUID]) -> dict[UUID, str | None]:
        """Nombre visible de cada usuario (`None` si fue suprimido o no tiene)."""
        ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> Session: ...

    async def save(self, session: Session) -> None: ...

    async def get(self, session_id: UUID) -> Session | None: ...

    async def add_refresh_token(self, token: RefreshToken) -> RefreshToken: ...

    async def save_refresh_token(self, token: RefreshToken) -> None: ...

    async def get_refresh_token_for_update(self, token_hash: bytes) -> RefreshToken | None:
        """Token por su hash, bloqueado hasta el fin de la transacción."""
        ...

    async def revoke_all_for_user(
        self, user_id: UUID, *, now: datetime, reason: RevocationReason
    ) -> int:
        """Revoca las sesiones activas del usuario (al incrementar `auth_epoch`, R-16)."""
        ...


class DeletionRequestRepository(Protocol):
    async def add(self, request: DeletionRequest) -> DeletionRequest:
        """Guarda la solicitud; lanza `DeletionAlreadyRequestedError` si ya hay una en curso."""
        ...

    async def save(self, request: DeletionRequest) -> None: ...

    async def open_for_user(self, user_id: UUID) -> DeletionRequest | None:
        """Solicitud del usuario que aún no se completa."""
        ...

    async def get_for_update(self, request_id: UUID) -> DeletionRequest | None:
        """Solicitud bloqueada hasta el fin de la transacción (`None` si otro proceso la tiene
        bloqueada o no existe)."""
        ...

    async def pending_ids(self, *, limit: int) -> list[UUID]:
        """Solicitudes sin completar, de la más antigua a la más reciente."""
        ...

    async def search(
        self, *, status: DeletionStatus | None, offset: int, limit: int
    ) -> tuple[list[DeletionRequest], int]:
        """Página de solicitudes, de la más reciente a la más antigua (FR-034)."""
        ...
