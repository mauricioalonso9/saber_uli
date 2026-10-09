"""Repositorio de solicitudes de supresión (data-model §2.12)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.deletion_request import (
    DeletionAlreadyRequestedError,
    DeletionOrigin,
    DeletionRequest,
    DeletionStatus,
)
from saber_uli.identity.infrastructure.orm import DeletionRequestRow

_OPEN = DeletionRequestRow.status != DeletionStatus.COMPLETED.value


def _to_domain(row: DeletionRequestRow) -> DeletionRequest:
    return DeletionRequest(
        id=row.id,
        user_id=row.user_id,
        origin=DeletionOrigin(row.origin),
        status=DeletionStatus(row.status),
        requested_at=row.requested_at,
        due_date=row.due_date,
        completed_at=row.completed_at,
    )


class SqlAlchemyDeletionRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, request: DeletionRequest) -> DeletionRequest:
        row = DeletionRequestRow(
            user_id=request.user_id,
            origin=request.origin.value,
            status=request.status.value,
            requested_at=request.requested_at,
            due_date=request.due_date,
        )
        self._session.add(row)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError as error:
            if "ux_deletion_requests_open" in str(error.orig):
                raise DeletionAlreadyRequestedError(
                    "Ya hay una solicitud de supresión en curso."
                ) from error
            raise
        request.id = row.id
        return request

    async def save(self, request: DeletionRequest) -> None:
        row = await self._session.get(DeletionRequestRow, request.id)
        if row is None:
            raise LookupError("la solicitud no existe")
        row.status = request.status.value
        row.completed_at = request.completed_at
        await self._session.flush()

    async def open_for_user(self, user_id: UUID) -> DeletionRequest | None:
        row = await self._session.scalar(
            select(DeletionRequestRow).where(DeletionRequestRow.user_id == user_id, _OPEN)
        )
        return _to_domain(row) if row else None

    async def get_for_update(self, request_id: UUID) -> DeletionRequest | None:
        row = await self._session.scalar(
            select(DeletionRequestRow)
            .where(DeletionRequestRow.id == request_id)
            .with_for_update(skip_locked=True)
        )
        return _to_domain(row) if row else None

    async def pending_ids(self, *, limit: int) -> list[UUID]:
        return list(
            await self._session.scalars(
                select(DeletionRequestRow.id)
                .where(_OPEN)
                .order_by(DeletionRequestRow.requested_at, DeletionRequestRow.id)
                .limit(limit)
            )
        )

    async def search(
        self, *, status: DeletionStatus | None, offset: int, limit: int
    ) -> tuple[list[DeletionRequest], int]:
        conditions = [] if status is None else [DeletionRequestRow.status == status.value]
        total = await self._session.scalar(
            select(func.count()).select_from(DeletionRequestRow).where(*conditions)
        )
        rows = await self._session.scalars(
            select(DeletionRequestRow)
            .where(*conditions)
            .order_by(DeletionRequestRow.requested_at.desc(), DeletionRequestRow.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_domain(row) for row in rows], int(total or 0)
