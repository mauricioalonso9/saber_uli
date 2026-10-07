"""Enlaces de acceso de invitados (data-model §2.8). Solo el hash del token."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.access_link import AccessLink, LinkPurpose
from saber_uli.identity.infrastructure.orm import AccessLinkRow


class SqlAlchemyAccessLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, link: AccessLink) -> AccessLink:
        row = AccessLinkRow(
            invitation_id=link.invitation_id,
            purpose=link.purpose.value,
            token_hash=link.token_hash,
            expires_at=link.expires_at,
            used_at=link.used_at,
            created_at=link.created_at,
        )
        self._db.add(row)
        await self._db.flush()
        link.id = row.id
        return link

    async def save(self, link: AccessLink) -> None:
        if link.id is None:
            raise ValueError("el enlace aún no se ha guardado; use add()")
        row = await self._db.get(AccessLinkRow, link.id)
        if row is None:
            raise LookupError("el enlace no existe")
        row.used_at = link.used_at
        await self._db.flush()

    async def get_by_hash_for_update(self, token_hash: bytes) -> AccessLink | None:
        row = await self._db.scalar(
            select(AccessLinkRow).where(AccessLinkRow.token_hash == token_hash).with_for_update()
        )
        return None if row is None else _to_domain(row)

    async def unused_for(self, invitation_id: UUID, purpose: LinkPurpose) -> list[AccessLink]:
        rows = await self._db.scalars(
            select(AccessLinkRow)
            .where(AccessLinkRow.invitation_id == invitation_id)
            .where(AccessLinkRow.purpose == purpose.value)
            .where(AccessLinkRow.used_at.is_(None))
            .with_for_update()
        )
        return [_to_domain(row) for row in rows]


def _to_domain(row: AccessLinkRow) -> AccessLink:
    return AccessLink(
        id=row.id,
        invitation_id=row.invitation_id,
        purpose=LinkPurpose(row.purpose),
        token_hash=row.token_hash,
        expires_at=row.expires_at,
        created_at=row.created_at,
        used_at=row.used_at,
    )
