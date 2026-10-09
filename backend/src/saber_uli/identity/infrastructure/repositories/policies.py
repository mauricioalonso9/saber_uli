"""Versiones de la política de tratamiento de datos (data-model §2.10).

Las versiones publicadas son inmutables: `saber_app` solo puede insertarlas y leerlas.
"""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.policy import PolicyVersion, PolicyVersionExistsError
from saber_uli.identity.infrastructure.orm import PolicyVersionRow


class SqlAlchemyPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def current(self, *, now: datetime) -> PolicyVersion | None:
        row = await self._db.scalar(
            select(PolicyVersionRow)
            .where(PolicyVersionRow.effective_from <= now)
            .order_by(PolicyVersionRow.effective_from.desc(), PolicyVersionRow.created_at.desc())
            .limit(1)
        )
        return None if row is None else _to_domain(row)

    async def get(self, version_id: UUID) -> PolicyVersion | None:
        row = await self._db.get(PolicyVersionRow, version_id)
        return None if row is None else _to_domain(row)

    async def versions(self) -> set[str]:
        return set(await self._db.scalars(select(PolicyVersionRow.version)))

    async def latest_effective_from(self) -> datetime | None:
        latest: datetime | None = await self._db.scalar(
            select(func.max(PolicyVersionRow.effective_from))
        )
        return latest

    async def add(self, version: PolicyVersion) -> PolicyVersion:
        row = PolicyVersionRow(
            version=version.version,
            title=version.title,
            body_markdown=version.body_markdown,
            effective_from=version.effective_from,
            published_by=version.published_by,
        )
        self._db.add(row)
        try:
            await self._db.flush()
        except IntegrityError as error:
            if "uq_policy_versions_version" in str(error.orig):
                raise PolicyVersionExistsError(
                    f"La versión {version.version} ya fue publicada."
                ) from error
            raise
        return replace(version, id=row.id)


def _to_domain(row: PolicyVersionRow) -> PolicyVersion:
    return PolicyVersion(
        id=row.id,
        version=row.version,
        title=row.title,
        body_markdown=row.body_markdown,
        effective_from=row.effective_from,
        published_by=row.published_by,
    )
