"""Lectura de autorizaciones y de la versión vigente de la política (data-model §2.10, §2.11)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.consent import ConsentDecision, ConsentRecord
from saber_uli.identity.infrastructure.orm import ConsentRow, PolicyVersionRow


class SqlAlchemyConsentReader:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def latest_for_user(self, user_id: UUID) -> ConsentRecord | None:
        row = await self._db.scalar(
            select(ConsentRow)
            .where(ConsentRow.user_id == user_id)
            .order_by(ConsentRow.decided_at.desc(), ConsentRow.id.desc())
            .limit(1)
        )
        if row is None:
            return None
        return ConsentRecord(
            policy_version_id=row.policy_version_id,
            decision=ConsentDecision(row.decision),
            decided_at=row.decided_at,
        )

    async def current_policy_version_id(self, *, now: datetime) -> UUID | None:
        """La versión vigente es la de mayor `effective_from ≤ now` (§2.10)."""
        version_id: UUID | None = await self._db.scalar(
            select(PolicyVersionRow.id)
            .where(PolicyVersionRow.effective_from <= now)
            .order_by(PolicyVersionRow.effective_from.desc())
            .limit(1)
        )
        return version_id
