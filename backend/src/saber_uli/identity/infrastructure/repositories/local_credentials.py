"""Credencial de la cuenta local de administración (data-model §2.16; ADR 0009)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.local_credential import LocalCredential
from saber_uli.identity.infrastructure.orm import LocalCredentialRow


class SqlAlchemyLocalCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, *, for_update: bool = False) -> LocalCredential | None:
        query = select(LocalCredentialRow).where(LocalCredentialRow.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        row = await self._session.scalar(query)
        if row is None:
            return None
        return LocalCredential(
            user_id=row.user_id,
            password_hash=row.password_hash,
            must_change=row.must_change,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
            changed_at=row.changed_at,
        )

    async def save(self, credential: LocalCredential) -> None:
        row = await self._session.get(LocalCredentialRow, credential.user_id)
        if row is None:
            raise LookupError("la credencial no existe")
        row.password_hash = credential.password_hash
        row.must_change = credential.must_change
        row.failed_attempts = credential.failed_attempts
        row.locked_until = credential.locked_until
        row.changed_at = credential.changed_at
        await self._session.flush()
