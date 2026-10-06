"""Estado del acceso de un invitado, derivado de su invitación (data-model §4.2)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.application.ports import GuestAccessStatus
from saber_uli.identity.infrastructure.orm import InvitationRow


class SqlAlchemyGuestAccessReader:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def status_for(self, user_id: UUID, *, now: datetime) -> GuestAccessStatus:
        row = (
            await self._db.execute(
                select(InvitationRow.status, InvitationRow.access_expires_at)
                .where(InvitationRow.guest_user_id == user_id)
                .order_by(InvitationRow.created_at.desc())
                .limit(1)
            )
        ).first()
        if row is None:
            return GuestAccessStatus.NONE
        status, access_expires_at = row
        if status == "revoked":
            return GuestAccessStatus.REVOKED
        if status == "expired" or access_expires_at <= now:
            return GuestAccessStatus.EXPIRED
        return GuestAccessStatus.ACTIVE
