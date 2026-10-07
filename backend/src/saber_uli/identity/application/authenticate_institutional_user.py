"""Ingreso con la cuenta institucional (FR-001 a FR-005; escenarios 1.1 a 1.3; R-11, R-12).

Recibe los claims ya validados por el adaptador de Entra ID (firma, `iss`, `aud`, `nonce`) y:

- rechaza otro inquilino (`tenant_not_allowed`) sin crear cuenta: tercera capa de R-11;
- identifica la cuenta por (`tid`, `oid`): la crea con rol Estudiante en el primer ingreso
  (auditado como `user.created`) o la reutiliza y actualiza nombre y correo del directorio;
- rechaza cuentas desactivadas o en supresión;
- registra el ingreso (`last_login_at`, base de la conservación de FR-034b).
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from saber_uli.identity.application.access_guard import AccountDeletedError, AccountDisabledError
from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.user import InstitutionalIdentity, User, UserStatus
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import PermissionDeniedError


class TenantNotAllowedError(PermissionDeniedError):
    """La cuenta Microsoft no pertenece al inquilino de la Universidad Libre (FR-002)."""

    slug = "tenant-not-allowed"
    code = "tenant_not_allowed"  # código de `/ingresar?error=` (contrato)


@dataclass(frozen=True)
class InstitutionalClaims:
    """Datos tomados del ID token (R-12): solo identificadores, nombre y correo."""

    tenant_id: UUID
    object_id: UUID
    name: str | None
    email: str


@dataclass(frozen=True)
class AuthenticationResult:
    user: User
    created: bool


class AuthenticateInstitutionalUser:
    def __init__(
        self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock, tenant_id: UUID
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._tenant_id = tenant_id

    async def execute(self, claims: InstitutionalClaims) -> AuthenticationResult:
        if claims.tenant_id != self._tenant_id:
            raise TenantNotAllowedError("Solo pueden ingresar cuentas de la Universidad Libre.")

        now = self._clock.now()
        identity = InstitutionalIdentity(tenant_id=claims.tenant_id, object_id=claims.object_id)
        display_name = (claims.name or "").strip() or claims.email

        async with self._uow_factory() as uow:
            user = await uow.users.get_by_entra_identity(identity)
            created = user is None
            if user is None:
                user = User.new_institutional(
                    identity, email=claims.email, display_name=display_name, now=now
                )
                user.record_login(now)
                await uow.users.add(user)
                await record_audit(
                    uow,
                    AuditAction.USER_CREATED,
                    target=AuditTarget.USER,
                    target_id=user.id,
                    subject_user_id=user.id,
                    details={"kind": user.kind.value, "roles": sorted(r.value for r in user.roles)},
                    now=now,
                )
            else:
                if user.status is UserStatus.DISABLED:
                    raise AccountDisabledError("La cuenta está desactivada.")
                if user.status is not UserStatus.ACTIVE:
                    raise AccountDeletedError("Esta cuenta fue eliminada.")
                user.record_login(now, email=claims.email, display_name=display_name)
                await uow.users.save(user)
            await uow.commit()
        return AuthenticationResult(user=user, created=created)
