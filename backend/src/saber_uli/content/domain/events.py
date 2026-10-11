"""Historia de los ítems (FR-018, FR-047; data-model §2.8 y §5).

Cada cambio de un ítem deja un evento con su actor (None = sistema), fecha, versión, comentario o
motivo y detalles sin datos personales. La historia es la auditoría del banco (research R-14).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class HistoryEventType(StrEnum):
    CREATED = "created"
    EDITED = "edited"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    RETURNED = "returned"
    REJECTED = "rejected"
    RETIRED = "retired"
    SUPERSEDED = "superseded"
    COMMENTED = "commented"
    IMPORTED = "imported"
    SEED_LOADED = "seed_loaded"
    SEED_VERSIONED = "seed_versioned"
    CONTEXT_CHANGED = "context_changed"
    REBASED_ON_CONTEXT = "rebased_on_context"


@dataclass(frozen=True)
class HistoryEvent:
    type: HistoryEventType
    version_number: int | None
    actor_id: UUID | None
    occurred_at: datetime
    comment: str | None = None
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    id: UUID | None = None  # lo asigna la persistencia
