"""Importación en lote (US4 y US5; FR-028 a FR-037; research R-05; data-model §2.9).

Una importación se valida completa y queda **pendiente** con el resultado de cada fila y el
contenido listo para aplicar; vence a las 24 horas. Al confirmarla entran todos los válidos o
ninguno, con la declaración de originalidad (FR-036).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from saber_uli.content.domain.diff import FieldChange
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.shared.domain.errors import ConflictError

PENDING_FOR = timedelta(hours=24)


class ImportAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    UNCHANGED = "unchanged"
    ERROR = "error"


class ImportStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


class ImportNotPendingError(ConflictError):
    slug = "import-not-pending"


class NothingToImportError(ConflictError):
    slug = "nothing-to-import"


@dataclass
class ImportRow:
    """Resultado de una entrada del archivo: ítem, consigna o contexto."""

    code: str
    entity: str
    action: ImportAction
    target_state: str | None = None
    changes: list[FieldChange] = field(default_factory=list)
    errors: list[ContentIssue] = field(default_factory=list)


@dataclass
class ImportJob:
    id: UUID | None
    created_by: UUID
    created_at: datetime
    source_name: str
    format: str
    file_sha256: bytes
    rows: list[ImportRow]
    payload: dict[str, Any] | None
    status: ImportStatus = ImportStatus.PENDING
    expires_at: datetime | None = None
    target_state: VersionState | None = None
    originality_declared: bool | None = None
    confirmed_at: datetime | None = None
    result: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.expires_at is None:
            self.expires_at = self.created_at + PENDING_FOR

    def counts(self) -> dict[str, int]:
        counts = {action.value: 0 for action in ImportAction}
        for row in self.rows:
            counts[row.action.value] += 1
        return counts

    def is_pending(self, now: datetime) -> bool:
        return (
            self.status is ImportStatus.PENDING
            and self.expires_at is not None
            and now < self.expires_at
        )

    def confirm(
        self,
        *,
        target_state: VersionState,
        now: datetime,
        created: int,
        versioned: int,
        skipped: list[str],
    ) -> None:
        if not self.is_pending(now):
            raise ImportNotPendingError("La importación ya se confirmó o venció.")
        self.status = ImportStatus.CONFIRMED
        self.target_state = target_state
        self.originality_declared = True
        self.confirmed_at = now
        self.result = {"created": created, "versioned": versioned, "skipped": skipped}
        self.payload = None
        mark_skipped(self.rows, skipped)


def mark_skipped(rows: list[ImportRow], skipped: list[str]) -> None:
    """Las filas omitidas al confirmar pasan a error `changed_since_preview`.

    Las filas no cambian en la base (solo cambian el estado y el resultado de la importación,
    data-model §2.9): esta marca se aplica al leer la importación confirmada.
    """
    omitted = set(skipped)
    for row in rows:
        if row.entity != "context" and row.code in omitted and row.action is not ImportAction.ERROR:
            row.action = ImportAction.ERROR
            row.errors = [
                ContentIssue(
                    "code",
                    ValidationRule.CHANGED_SINCE_PREVIEW,
                    "Otra persona creó o cambió este ítem después de la vista previa.",
                )
            ]
