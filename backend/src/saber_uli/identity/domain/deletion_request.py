"""Solicitud de supresión (data-model §2.12 y §4.3; FR-032, FR-034).

```text
received ──► in_progress ──► completed
```

La fecha límite es la fecha de la solicitud más 15 días hábiles en Colombia (R-25). El
procesamiento es idempotente: reanudar una solicitud `in_progress` completa lo que falta.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from saber_uli.identity.domain.business_days import deletion_due_date
from saber_uli.shared.domain.errors import ConflictError


class DeletionStatus(StrEnum):
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class DeletionOrigin(StrEnum):
    USER_REQUEST = "user_request"
    GUEST_RETENTION = "guest_retention"
    INSTITUTIONAL_RETENTION = "institutional_retention"


class DeletionAlreadyRequestedError(ConflictError):
    slug = "deletion-already-requested"


@dataclass(eq=False)
class DeletionRequest:
    user_id: UUID
    origin: DeletionOrigin
    status: DeletionStatus
    requested_at: datetime
    due_date: date
    id: UUID | None = None
    completed_at: datetime | None = None

    @classmethod
    def open(cls, user_id: UUID, origin: DeletionOrigin, *, now: datetime) -> "DeletionRequest":
        return cls(
            user_id=user_id,
            origin=origin,
            status=DeletionStatus.RECEIVED,
            requested_at=now,
            due_date=deletion_due_date(now),
        )

    @property
    def is_completed(self) -> bool:
        return self.status is DeletionStatus.COMPLETED

    def start(self) -> None:
        if self.status is DeletionStatus.RECEIVED:
            self.status = DeletionStatus.IN_PROGRESS

    def complete(self, now: datetime) -> None:
        if self.status is not DeletionStatus.COMPLETED:
            self.status = DeletionStatus.COMPLETED
            self.completed_at = now
