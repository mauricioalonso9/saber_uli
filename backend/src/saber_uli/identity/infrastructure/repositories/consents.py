"""Autorizaciones y versión vigente de la política (data-model §2.10, §2.11).

`saber_app` solo puede insertar y leer `consents`: la revocación es un registro más.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.application.ports import ConsentEntry
from saber_uli.identity.domain.consent import ConsentDecision, ConsentRecord
from saber_uli.identity.infrastructure.orm import ConsentRow, PolicyVersionRow


class SqlAlchemyConsentRepository:
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
            channel=row.channel,
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

    async def history_for_user(self, user_id: UUID) -> list[ConsentEntry]:
        rows = await self._db.execute(
            select(ConsentRow, PolicyVersionRow.version)
            .join(PolicyVersionRow, PolicyVersionRow.id == ConsentRow.policy_version_id)
            .where(ConsentRow.user_id == user_id)
            .order_by(ConsentRow.decided_at.desc(), ConsentRow.id.desc())
        )
        return [_entry(row, version) for row, version in rows]

    async def add(self, user_id: UUID, record: ConsentRecord) -> ConsentEntry:
        row = ConsentRow(
            user_id=user_id,
            policy_version_id=record.policy_version_id,
            decision=record.decision.value,
            channel=record.channel,
            decided_at=record.decided_at,
        )
        self._db.add(row)
        await self._db.flush()
        version = (
            await self._db.execute(
                select(PolicyVersionRow.version).where(PolicyVersionRow.id == row.policy_version_id)
            )
        ).scalar_one()
        return _entry(row, version)


def _entry(row: ConsentRow, version: str) -> ConsentEntry:
    return ConsentEntry(
        id=row.id,
        policy_version_id=row.policy_version_id,
        policy_version=version,
        decision=ConsentDecision(row.decision),
        channel=row.channel,
        decided_at=row.decided_at,
    )
