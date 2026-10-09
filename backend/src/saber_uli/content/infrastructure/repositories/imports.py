"""Importaciones pendientes, confirmadas y vencidas (data-model §2.9; research R-05).

`saber_app` solo puede cambiar el estado, el contenido por aplicar y el resultado (permisos de
columna): `save` actualiza solo esas columnas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.domain.diff import FieldChange
from saber_uli.content.domain.import_job import (
    ImportAction,
    ImportJob,
    ImportRow,
    ImportStatus,
    mark_skipped,
)
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.content.infrastructure.orm import ImportRow as ImportTable


class SqlAlchemyImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, job: ImportJob) -> ImportJob:
        row = ImportTable(
            created_by=job.created_by,
            created_at=job.created_at,
            source_name=job.source_name,
            format=job.format,
            file_sha256=job.file_sha256,
            status=job.status.value,
            expires_at=job.expires_at,
            summary=job.counts(),
            rows=[_row_out(value) for value in job.rows],
            payload=job.payload,
        )
        self._db.add(row)
        await self._db.flush()
        job.id = row.id
        return job

    async def get(self, import_id: UUID, *, for_update: bool = False) -> ImportJob | None:
        query = select(ImportTable).where(ImportTable.id == import_id)
        if for_update:
            query = query.with_for_update()
        row = await self._db.scalar(query)
        return None if row is None else _job(row)

    async def save(self, job: ImportJob) -> None:
        await self._db.execute(
            update(ImportTable)
            .where(ImportTable.id == job.id)
            .values(
                status=job.status.value,
                payload=job.payload,
                target_state=None if job.target_state is None else job.target_state.value,
                originality_declared=job.originality_declared,
                confirmed_at=job.confirmed_at,
                result=job.result,
            )
        )

    async def list(
        self, *, created_by: UUID | None, offset: int, limit: int
    ) -> tuple[list[ImportJob], int]:
        query = select(ImportTable)
        count = select(func.count()).select_from(ImportTable)
        if created_by is not None:
            query = query.where(ImportTable.created_by == created_by)
            count = count.where(ImportTable.created_by == created_by)
        rows = await self._db.scalars(
            query.order_by(ImportTable.created_at.desc(), ImportTable.id)
            .offset(offset)
            .limit(limit)
        )
        return [_job(row) for row in rows], int(await self._db.scalar(count) or 0)

    async def expire_pending(self, now: datetime) -> int:
        result = await self._db.execute(
            update(ImportTable)
            .where(ImportTable.status == ImportStatus.PENDING.value, ImportTable.expires_at <= now)
            .values(status=ImportStatus.EXPIRED.value, payload=None)
            .returning(ImportTable.id)
        )
        return len(result.all())


def _row_out(value: ImportRow) -> dict[str, Any]:
    return {
        "code": value.code,
        "entity": value.entity,
        "action": value.action.value,
        "target_state": value.target_state,
        "changes": [
            {"field": change.field, "before": change.before, "after": change.after}
            for change in value.changes
        ],
        "errors": [
            {"field": issue.field, "rule": issue.rule.value, "message": issue.message}
            for issue in value.errors
        ],
    }


def _row_in(data: dict[str, Any]) -> ImportRow:
    return ImportRow(
        code=data["code"],
        entity=data["entity"],
        action=ImportAction(data["action"]),
        target_state=data.get("target_state"),
        changes=[FieldChange(c["field"], c.get("before"), c.get("after")) for c in data["changes"]],
        errors=[
            ContentIssue(e["field"], ValidationRule(e["rule"]), e["message"])
            for e in data["errors"]
        ],
    )


def _job(row: ImportTable) -> ImportJob:
    job = ImportJob(
        id=row.id,
        created_by=row.created_by,
        created_at=row.created_at,
        source_name=row.source_name,
        format=row.format,
        file_sha256=row.file_sha256,
        rows=[_row_in(value) for value in row.rows],
        payload=row.payload,
        status=ImportStatus(row.status),
        expires_at=row.expires_at,
        target_state=None if row.target_state is None else VersionState(row.target_state),
        originality_declared=row.originality_declared,
        confirmed_at=row.confirmed_at,
        result=row.result,
    )
    if job.result is not None:
        mark_skipped(job.rows, list(job.result.get("skipped", [])))
    return job
