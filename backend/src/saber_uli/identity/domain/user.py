"""Agregado `User` (data-model §2.1 y §4.1).

- La identidad institucional es el par (`tid`, `oid`) de Entra ID (R-12, FR-005).
- `auth_epoch` se incrementa en cada transición que revoca sesiones (R-16): desactivar, solicitar
  la supresión, retirar un rol o `invalidate_sessions()` (revocar la autorización de datos o el
  acceso de invitado).
- `deleted` es final; la lápida no conserva datos personales (FR-033).
- Reglas de roles del dominio: el invitado no tiene otros roles (FR-024) y el institucional
  conserva siempre `student`. La regla del último administrador (FR-025) necesita bloquear filas
  y vive en la capa de aplicación.

El `id` lo asigna la base de datos (`uuidv7()`, R-06): un usuario nuevo tiene `id = None` hasta
que el repositorio lo guarda.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from saber_uli.identity.domain.permissions import Permission, permissions_for
from saber_uli.identity.domain.roles import Role, has_privileged_role
from saber_uli.shared.domain.errors import ConflictError


class UserKind(StrEnum):
    INSTITUTIONAL = "institutional"
    GUEST = "guest"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class InvalidUserTransitionError(ConflictError):
    """Transición de estado no permitida por data-model §4.1."""


class GuestRoleExclusiveError(ConflictError):
    slug = "guest-role-exclusive"


class StudentRoleRequiredError(ConflictError):
    slug = "student-role-required"


@dataclass(frozen=True)
class InstitutionalIdentity:
    tenant_id: UUID
    object_id: UUID


@dataclass(eq=False)
class User:
    kind: UserKind
    status: UserStatus
    email: str | None
    display_name: str | None
    created_at: datetime
    roles: set[Role] = field(default_factory=set)
    entra_identity: InstitutionalIdentity | None = None
    id: UUID | None = None
    auth_epoch: int = 0
    last_login_at: datetime | None = None
    retention_notice_sent_at: datetime | None = None
    onboarding_completed_at: datetime | None = None

    # --- Creación -------------------------------------------------------------------------

    @classmethod
    def new_institutional(
        cls, identity: InstitutionalIdentity, *, email: str, display_name: str, now: datetime
    ) -> "User":
        """Primer ingreso con Microsoft: cuenta institucional con rol Estudiante (FR-003)."""
        return cls(
            kind=UserKind.INSTITUTIONAL,
            status=UserStatus.ACTIVE,
            entra_identity=identity,
            email=email,
            display_name=display_name,
            roles={Role.STUDENT},
            created_at=now,
        )

    @classmethod
    def new_guest(cls, *, email: str, display_name: str | None, now: datetime) -> "User":
        return cls(
            kind=UserKind.GUEST,
            status=UserStatus.ACTIVE,
            email=email,
            display_name=display_name,
            roles={Role.GUEST},
            created_at=now,
        )

    # --- Consultas ------------------------------------------------------------------------

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.roles)

    @property
    def has_privileged_role(self) -> bool:
        return has_privileged_role(self.roles)

    @property
    def is_active(self) -> bool:
        return self.status is UserStatus.ACTIVE

    # --- Transiciones (§4.1) ----------------------------------------------------------------

    def _require(self, *allowed: UserStatus) -> None:
        if self.status not in allowed:
            raise InvalidUserTransitionError(
                "La acción no es posible en el estado actual de la cuenta."
            )

    def invalidate_sessions(self) -> None:
        """Revoca todas las sesiones del usuario en su siguiente petición (R-16)."""
        self.auth_epoch += 1

    def disable(self) -> None:
        self._require(UserStatus.ACTIVE)
        self.status = UserStatus.DISABLED
        self.invalidate_sessions()

    def reactivate(self) -> None:
        self._require(UserStatus.DISABLED)
        self.status = UserStatus.ACTIVE

    def request_deletion(self) -> None:
        self._require(UserStatus.ACTIVE, UserStatus.DISABLED)
        self.status = UserStatus.DELETION_PENDING
        self.invalidate_sessions()

    def to_tombstone(self) -> None:
        """Fin de la supresión: queda solo el UUID (FR-033)."""
        self._require(UserStatus.DELETION_PENDING)
        self.status = UserStatus.DELETED
        self.email = None
        self.display_name = None
        self.entra_identity = None
        self.roles = set()
        self.retention_notice_sent_at = None

    def record_login(
        self, now: datetime, *, email: str | None = None, display_name: str | None = None
    ) -> None:
        """Ingreso o renovación: actualiza los datos del directorio (FR-005) y reinicia el plazo
        de conservación (FR-034b/c)."""
        self._require(UserStatus.ACTIVE)
        self.last_login_at = now
        self.retention_notice_sent_at = None
        if email:
            self.email = email
        if display_name:
            self.display_name = display_name

    # --- Roles (FR-023, FR-024) -----------------------------------------------------------

    def grant_role(self, role: Role) -> None:
        self._require(UserStatus.ACTIVE, UserStatus.DISABLED)
        if (self.kind is UserKind.GUEST) != (role is Role.GUEST):
            raise GuestRoleExclusiveError(
                "Un invitado no puede tener otros roles ni un institucional el rol Invitado."
            )
        self.roles.add(role)

    def revoke_role(self, role: Role) -> None:
        self._require(UserStatus.ACTIVE, UserStatus.DISABLED)
        if role not in self.roles:
            return
        if self.kind is UserKind.INSTITUTIONAL and role is Role.STUDENT:
            raise StudentRoleRequiredError("Una cuenta institucional conserva el rol Estudiante.")
        self.roles.discard(role)
        self.invalidate_sessions()
