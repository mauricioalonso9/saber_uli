"""Invitaciones de invitados (data-model §2.7)."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.invitation import (
    Invitation,
    InvitationAlreadyActiveError,
    InvitationStatus,
)
from saber_uli.identity.infrastructure.orm import InvitationRow

_ACTIVE = (InvitationStatus.SENT.value, InvitationStatus.ACCEPTED.value)


class SqlAlchemyInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, invitation: Invitation) -> Invitation:
        row = InvitationRow(created_at=invitation.created_at)
        _copy(invitation, row)
        self._db.add(row)
        try:
            await self._db.flush()
        except IntegrityError as error:
            if "ux_invitations_active_email" in str(error.orig):
                raise InvitationAlreadyActiveError(
                    "Esa persona ya tiene una invitación vigente."
                ) from error
            raise
        invitation.id = row.id
        return invitation

    async def save(self, invitation: Invitation) -> None:
        if invitation.id is None:
            raise ValueError("la invitación aún no se ha guardado; use add()")
        row = await self._db.get(InvitationRow, invitation.id)
        if row is None:
            raise LookupError("la invitación no existe")
        _copy(invitation, row)
        row.updated_at = func.now()
        await self._db.flush()

    async def get_for_update(self, invitation_id: UUID) -> Invitation | None:
        row = await self._db.scalar(
            select(InvitationRow).where(InvitationRow.id == invitation_id).with_for_update()
        )
        return None if row is None else _to_domain(row)

    async def get(self, invitation_id: UUID) -> Invitation | None:
        row = await self._db.get(InvitationRow, invitation_id)
        return None if row is None else _to_domain(row)

    async def search(
        self,
        *,
        invited_by: UUID | None,
        status: InvitationStatus | None,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Invitation], int]:
        conditions = []
        if invited_by is not None:
            conditions.append(InvitationRow.invited_by == invited_by)
        if status is not None:
            conditions.append(InvitationRow.status == status.value)
        if q:
            escaped = (
                q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            conditions.append(
                func.lower(InvitationRow.email).like(pattern, escape="\\")
                | func.lower(InvitationRow.invitee_name).like(pattern, escape="\\")
            )
        total = await self._db.scalar(
            select(func.count()).select_from(InvitationRow).where(*conditions)
        )
        rows = await self._db.scalars(
            select(InvitationRow)
            .where(*conditions)
            .order_by(InvitationRow.created_at.desc(), InvitationRow.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_domain(row) for row in rows], int(total or 0)

    async def active_emails(self, emails: Collection[str]) -> set[str]:
        wanted = {email.strip().lower() for email in emails}
        if not wanted:
            return set()
        rows = await self._db.scalars(
            select(func.lower(InvitationRow.email))
            .where(func.lower(InvitationRow.email).in_(wanted))
            .where(InvitationRow.status.in_(_ACTIVE))
        )
        return set(rows)

    async def find_active_by_email(self, email: str) -> Invitation | None:
        row = await self._db.scalar(
            select(InvitationRow)
            .where(func.lower(InvitationRow.email) == email.strip().lower())
            .where(InvitationRow.status.in_(_ACTIVE))
            .order_by(InvitationRow.created_at.desc())
            .limit(1)
        )
        return None if row is None else _to_domain(row)

    async def set_delivery_status(self, invitation_id: UUID, status: str) -> None:
        await self._db.execute(
            update(InvitationRow)
            .where(InvitationRow.id == invitation_id)
            .values(last_delivery_status=status, updated_at=func.now())
        )


def _copy(invitation: Invitation, row: InvitationRow) -> None:
    row.email = invitation.email
    row.invitee_name = invitation.invitee_name
    row.invited_by = invitation.invited_by
    row.batch_id = invitation.batch_id
    row.guest_user_id = invitation.guest_user_id
    row.status = invitation.status.value
    row.access_expires_at = invitation.access_expires_at
    row.link_expires_at = invitation.link_expires_at
    row.sent_at = invitation.sent_at
    row.accepted_at = invitation.accepted_at
    row.revoked_at = invitation.revoked_at


def _to_domain(row: InvitationRow) -> Invitation:
    return Invitation(
        id=row.id,
        email=row.email,
        invited_by=row.invited_by,
        access_expires_at=row.access_expires_at,
        status=InvitationStatus(row.status),
        created_at=row.created_at,
        invitee_name=row.invitee_name,
        batch_id=row.batch_id,
        guest_user_id=row.guest_user_id,
        link_expires_at=row.link_expires_at,
        sent_at=row.sent_at,
        accepted_at=row.accepted_at,
        revoked_at=row.revoked_at,
    )
