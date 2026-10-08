"""Administración de cuentas (FR-023 a FR-026, FR-029; data-model §4.1).

- Roles: el administrador define todos los roles de una persona (y los programas que dirige);
  retirar un rol cierra sus sesiones. Cada cambio se audita con los roles antes y después.
- Estado: desactivar cierra las sesiones de inmediato; reactivar devuelve el ingreso, no las
  sesiones anteriores.
- Último administrador (FR-025): retirar el rol o desactivar al único administrador activo se
  rechaza. Se bloquean las filas de los administradores activos, así dos administradores que se
  quitan el rol a la vez no pueden dejar el sistema sin ninguno.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import GuestAccessStatus
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.events import UserAccessChanged
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import User, UserKind, UserStatus
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import ConflictError, NotFoundError

VisibleStatus = Literal[
    "active", "disabled", "guest_expired", "guest_revoked", "deletion_pending", "deleted"
]


class LastAdminError(ConflictError):
    slug = "last-admin"


class UnknownProgramError(ConflictError):
    slug = "unknown-program"


class UserNotFoundError(NotFoundError):
    slug = "not-found"


class NotInstitutionalAccountError(ConflictError):
    slug = "not-institutional-account"


@dataclass(frozen=True)
class AdminUserView:
    user: User
    status: VisibleStatus
    director_programs: list[Program]


class AdminUsersService:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    # --- Consultas ------------------------------------------------------------------------

    async def list(
        self,
        *,
        q: str | None = None,
        kind: UserKind | None = None,
        role: Role | None = None,
        status: VisibleStatus | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[AdminUserView], int]:
        async with self._uow_factory() as uow:
            users, total = await uow.users.search(
                q=q, kind=kind, role=role, status=status, offset=offset, limit=limit
            )
            return [await self._view(uow, user) for user in users], total

    async def get(self, user_id: UUID) -> AdminUserView:
        async with self._uow_factory() as uow:
            return await self._view(uow, await _existing(uow, user_id))

    # --- Cambios --------------------------------------------------------------------------

    async def set_status(
        self, actor_id: UUID, user_id: UUID, status: Literal["active", "disabled"]
    ) -> AdminUserView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await _existing(uow, user_id)
            if status == "disabled" and user.status is UserStatus.ACTIVE:
                if Role.ADMIN in user.roles:
                    await ensure_other_admin(uow, user_id)
                user.disable()
                await uow.sessions.revoke_all_for_user(user_id, now=now, reason="access_changed")
                uow.record(UserAccessChanged(user_id=user_id, occurred_at=now))
                action = AuditAction.USER_DISABLED
            elif status == "active" and user.status is UserStatus.DISABLED:
                user.reactivate()
                action = AuditAction.USER_REACTIVATED
            else:
                return await self._view(uow, user)  # ya estaba así: sin cambios ni auditoría
            await uow.users.save(user)
            await record_audit(
                uow,
                action,
                target=AuditTarget.USER,
                target_id=user_id,
                subject_user_id=user_id,
                actor_id=actor_id,
                now=now,
            )
            view = await self._view(uow, user)
            await uow.commit()
        return view

    async def set_roles(
        self,
        actor_id: UUID,
        user_id: UUID,
        roles: set[Role],
        *,
        director_program_ids: set[UUID],
    ) -> AdminUserView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await _existing(uow, user_id)
            before_roles = sorted(role.value for role in user.roles)
            before_programs = set(user.director_program_ids)
            if Role.ADMIN in user.roles and Role.ADMIN not in roles:
                await ensure_other_admin(uow, user_id)
            if Role.PROGRAM_DIRECTOR in roles:
                for program_id in director_program_ids:
                    if await uow.programs.get(program_id) is None:
                        raise UnknownProgramError("Uno de los programas elegidos no existe.")
            granted, revoked = user.set_roles(roles, director_program_ids=director_program_ids)
            await uow.users.save(user)
            after_roles = sorted(role.value for role in user.roles)
            for action, changed in (
                (AuditAction.USER_ROLE_GRANTED, granted),
                (AuditAction.USER_ROLE_REVOKED, revoked),
            ):
                if changed:
                    await record_audit(
                        uow,
                        action,
                        target=AuditTarget.USER,
                        target_id=user_id,
                        subject_user_id=user_id,
                        actor_id=actor_id,
                        details={
                            "roles": sorted(role.value for role in changed),
                            "before": before_roles,
                            "after": after_roles,
                        },
                        now=now,
                    )
            if user.director_program_ids != before_programs:
                await record_audit(
                    uow,
                    AuditAction.USER_DIRECTOR_PROGRAMS_CHANGED,
                    target=AuditTarget.USER,
                    target_id=user_id,
                    subject_user_id=user_id,
                    actor_id=actor_id,
                    details={"program_ids": sorted(str(p) for p in user.director_program_ids)},
                    now=now,
                )
            if revoked:
                await uow.sessions.revoke_all_for_user(user_id, now=now, reason="access_changed")
                uow.record(UserAccessChanged(user_id=user_id, occurred_at=now))
            view = await self._view(uow, user)
            await uow.commit()
        return view

    async def grant_admin_by_email(self, email: str) -> bool:
        """Primer administrador (R-28, comando `grant-admin`): actor sistema. Devuelve `False` si
        ya era administrador."""
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.find_by_email(email)
            if user is None or user.id is None:
                raise UserNotFoundError(
                    "No hay una cuenta con ese correo: la persona debe ingresar una vez con su "
                    "cuenta Unilibre."
                )
            if user.kind is not UserKind.INSTITUTIONAL:
                raise NotInstitutionalAccountError(
                    "Solo una cuenta institucional puede ser administradora."
                )
            if Role.ADMIN in user.roles:
                return False
            before = sorted(role.value for role in user.roles)
            user.grant_role(Role.ADMIN)
            await uow.users.save(user)
            await record_audit(
                uow,
                AuditAction.USER_ROLE_GRANTED,
                target=AuditTarget.USER,
                target_id=user.id,
                subject_user_id=user.id,
                details={
                    "roles": ["admin"],
                    "before": before,
                    "after": sorted(role.value for role in user.roles),
                },
                now=now,
            )
            await uow.commit()
        return True

    # --- Auxiliares -----------------------------------------------------------------------

    async def _view(self, uow: IdentityUnitOfWork, user: User) -> AdminUserView:
        programs = [
            program
            for program_id in sorted(user.director_program_ids)
            if (program := await uow.programs.get(program_id)) is not None
        ]
        return AdminUserView(
            user=user,
            status=await _visible_status(uow, user, self._clock),
            director_programs=programs,
        )


async def _existing(uow: IdentityUnitOfWork, user_id: UUID) -> User:
    user = await uow.users.get(user_id)
    if user is None:
        raise UserNotFoundError("La cuenta no existe.")
    return user


async def ensure_other_admin(
    uow: IdentityUnitOfWork,
    user_id: UUID,
    *,
    message: str = "No puedes quitar el rol Administrador al último administrador activo.",
) -> None:
    """FR-025 y FR-034d: bloquea a los administradores activos y exige otro además de
    `user_id`. Comparten el bloqueo los cambios de roles, la desactivación y la supresión."""
    if not await has_other_active_admin(uow, user_id):
        raise LastAdminError(message)


async def has_other_active_admin(uow: IdentityUnitOfWork, user_id: UUID) -> bool:
    admins = await uow.users.lock_active_admins()
    return any(admin != user_id for admin in admins)


async def _visible_status(uow: IdentityUnitOfWork, user: User, clock: Clock) -> VisibleStatus:
    if user.kind is UserKind.GUEST and user.status is UserStatus.ACTIVE and user.id is not None:
        access = await uow.guest_access.status_for(user.id, now=clock.now())
        if access is GuestAccessStatus.REVOKED:
            return "guest_revoked"
        if access is GuestAccessStatus.EXPIRED:
            return "guest_expired"
    return user.status.value
