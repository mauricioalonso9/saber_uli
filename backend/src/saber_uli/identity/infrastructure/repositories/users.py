"""Repositorio de usuarios con SQLAlchemy (data-model §2.1 y §2.3)."""

from collections.abc import Collection
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.application.ports import UserAlreadyExistsError
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import InstitutionalIdentity, User, UserKind, UserStatus
from saber_uli.identity.infrastructure.orm import (
    DirectorProgramRow,
    InvitationRow,
    RoleAssignmentRow,
    UserRow,
)
from saber_uli.shared.infrastructure.db import LIKE_ESCAPE, contains_pattern


def _to_domain(row: UserRow) -> User:
    identity = (
        InstitutionalIdentity(tenant_id=row.entra_tenant_id, object_id=row.entra_object_id)
        if row.entra_tenant_id is not None and row.entra_object_id is not None
        else None
    )
    return User(
        id=row.id,
        kind=UserKind(row.kind),
        status=UserStatus(row.status),
        entra_identity=identity,
        email=row.email,
        display_name=row.display_name,
        roles={Role(assignment.role) for assignment in row.role_assignments},
        auth_epoch=row.auth_epoch,
        last_login_at=row.last_login_at,
        retention_notice_sent_at=row.retention_notice_sent_at,
        onboarding_completed_at=row.onboarding_completed_at,
        created_at=row.created_at,
        director_program_ids={link.program_id for link in row.director_programs},
    )


def _copy_fields(user: User, row: UserRow) -> None:
    row.kind = user.kind.value
    row.status = user.status.value
    # La lápida conserva el inquilino (no es dato personal) pero no el `oid` (FR-033).
    if user.entra_identity is not None:
        row.entra_tenant_id = user.entra_identity.tenant_id
        row.entra_object_id = user.entra_identity.object_id
    else:
        row.entra_object_id = None
    row.email = user.email
    row.display_name = user.display_name
    row.auth_epoch = user.auth_epoch
    row.last_login_at = user.last_login_at
    row.retention_notice_sent_at = user.retention_notice_sent_at
    row.onboarding_completed_at = user.onboarding_completed_at


def _sync_roles(user: User, row: UserRow) -> None:
    current = {assignment.role for assignment in row.role_assignments}
    wanted = {role.value for role in user.roles}
    row.role_assignments = [a for a in row.role_assignments if a.role in wanted]
    row.role_assignments.extend(RoleAssignmentRow(role=role) for role in sorted(wanted - current))
    linked = {link.program_id for link in row.director_programs}
    row.director_programs = [
        link for link in row.director_programs if link.program_id in user.director_program_ids
    ]
    row.director_programs.extend(
        DirectorProgramRow(program_id=program_id)
        for program_id in sorted(user.director_program_ids - linked)
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        row = UserRow(created_at=user.created_at)
        _copy_fields(user, row)
        _sync_roles(user, row)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as error:
            if "uq_users_entra_identity" in str(error.orig):
                raise UserAlreadyExistsError from error
            raise
        user.id = row.id
        return user

    async def save(self, user: User) -> None:
        if user.id is None:
            raise ValueError("el usuario aún no se ha guardado; use add()")
        row = await self._session.get(UserRow, user.id)
        if row is None:
            raise LookupError("el usuario no existe")
        _copy_fields(user, row)
        _sync_roles(user, row)
        row.updated_at = func.now()
        await self._session.flush()

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return _to_domain(row) if row else None

    async def get_by_entra_identity(self, identity: InstitutionalIdentity) -> User | None:
        row = await self._session.scalar(
            select(UserRow).where(
                UserRow.entra_tenant_id == identity.tenant_id,
                UserRow.entra_object_id == identity.object_id,
            )
        )
        return _to_domain(row) if row else None

    async def find_by_email(self, email: str) -> User | None:
        row = await self._session.scalar(
            select(UserRow)
            .where(func.lower(UserRow.email) == email.strip().lower())
            .where(UserRow.status != UserStatus.DELETED.value)
            .order_by(UserRow.created_at.desc())
            .limit(1)
        )
        return _to_domain(row) if row else None

    async def find_active_guest_by_email(self, email: str) -> User | None:
        row = await self._session.scalar(
            select(UserRow).where(
                UserRow.kind == UserKind.GUEST.value,
                UserRow.status != UserStatus.DELETED.value,
                func.lower(UserRow.email) == email.strip().lower(),
            )
        )
        return _to_domain(row) if row else None

    async def lock_active_admins(self) -> list[UUID]:
        admins = (
            select(UserRow.id)
            .join(RoleAssignmentRow, RoleAssignmentRow.user_id == UserRow.id)
            .where(
                RoleAssignmentRow.role == Role.ADMIN.value,
                UserRow.status == UserStatus.ACTIVE.value,
            )
            .order_by(UserRow.id)
        )
        # 1) Bloquea las filas de los administradores en orden (sin interbloqueos): quien llegue
        #    segundo espera a que la otra transacción confirme.
        await self._session.execute(admins.with_for_update(of=UserRow))
        # 2) Vuelve a leer con una consulta nueva (READ COMMITTED: instantánea nueva). Tras la
        #    espera, PostgreSQL revisa la fila de `users` bloqueada pero no el join con
        #    `role_assignments`: la primera lectura aún podría contar un rol ya retirado.
        return list(await self._session.scalars(admins))

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
        conditions: list[Any] = []
        if q:
            pattern = contains_pattern(q)
            conditions.append(
                func.lower(UserRow.email).like(pattern, escape=LIKE_ESCAPE)
                | func.lower(UserRow.display_name).like(pattern, escape=LIKE_ESCAPE)
            )
        if kind is not None:
            conditions.append(UserRow.kind == kind.value)
        if role is not None:
            conditions.append(
                exists().where(
                    RoleAssignmentRow.user_id == UserRow.id, RoleAssignmentRow.role == role.value
                )
            )
        if status in ("guest_expired", "guest_revoked"):
            conditions += [
                UserRow.kind == UserKind.GUEST.value,
                UserRow.status == UserStatus.ACTIVE.value,
                exists().where(
                    InvitationRow.guest_user_id == UserRow.id,
                    InvitationRow.status == ("expired" if status == "guest_expired" else "revoked"),
                ),
            ]
        elif status is not None:
            conditions.append(UserRow.status == status)
        total = await self._session.scalar(
            select(func.count()).select_from(UserRow).where(*conditions)
        )
        rows = await self._session.scalars(
            select(UserRow)
            .where(*conditions)
            .order_by(UserRow.created_at.desc(), UserRow.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_domain(row) for row in rows], int(total or 0)

    async def display_names(self, user_ids: Collection[UUID]) -> dict[UUID, str | None]:
        if not user_ids:
            return {}
        rows = await self._session.execute(
            select(UserRow.id, UserRow.display_name).where(UserRow.id.in_(list(user_ids)))
        )
        return {row.id: row.display_name for row in rows}
