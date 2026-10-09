"""Borrado de los datos personales que cuelgan de un usuario (FR-033; research R-25).

Las filas que solo enlazan el UUID y sirven de prueba se conservan: autorizaciones
(`consents`), auditoría y el contenido que la persona creó (grupos, invitaciones que envió).
"""

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.infrastructure.orm import (
    AccessLinkRow,
    GroupMemberRow,
    GroupTeacherRow,
    InvitationRow,
    ProfileRow,
    SessionRow,
)


class SqlAlchemyPersonalDataEraser:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def erase(self, user_id: UUID) -> None:
        db = self._session
        await db.execute(delete(ProfileRow).where(ProfileRow.user_id == user_id))
        await db.execute(delete(GroupMemberRow).where(GroupMemberRow.user_id == user_id))
        await db.execute(delete(GroupTeacherRow).where(GroupTeacherRow.user_id == user_id))
        # Los tokens de renovación se borran en cascada con su sesión.
        await db.execute(delete(SessionRow).where(SessionRow.user_id == user_id))

        invitations = select(InvitationRow.id).where(InvitationRow.guest_user_id == user_id)
        await db.execute(delete(AccessLinkRow).where(AccessLinkRow.invitation_id.in_(invitations)))
        await db.execute(
            update(InvitationRow)
            .where(InvitationRow.guest_user_id == user_id)
            .values(email=None, invitee_name=None, updated_at=func.now())
        )
        await db.flush()
