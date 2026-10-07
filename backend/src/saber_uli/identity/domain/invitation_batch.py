"""Lotes de invitaciones (FR-009; escenario 5.2; SC-005; data-model §2.9).

Un lote se valida fila por fila y queda 24 horas pendiente de confirmación; al confirmarlo se
crean solo las filas válidas. El CSV es UTF-8 (con o sin BOM) con encabezado
`correo,nombre,vence`; `vence` es una fecha `AAAA-MM-DD` y el acceso dura hasta el final de ese
día en Colombia. Máximo 500 filas.
"""

import csv
import io
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from saber_uli.identity.domain.invitation import (
    AccessExpiryOutOfRangeError,
    is_institutional_email,
    validate_access_expiry,
)
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

BATCH_MAX_ROWS = 500
BATCH_TTL = timedelta(hours=24)
CSV_HEADER = ["correo", "nombre", "vence"]
COLOMBIA = timezone(timedelta(hours=-5))  # sin horario de verano
_EMAIL = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")


class BatchTooLargeError(RuleViolationError):
    """Más de 500 filas (413 en el contrato)."""

    slug = "batch-too-large"


class InvalidBatchFileError(RuleViolationError):
    slug = "validation-error"


class BatchNotPendingError(ConflictError):
    slug = "batch-not-pending"


class BatchStatus(StrEnum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


class RowResult(StrEnum):
    VALID = "valid"
    INVALID_EMAIL = "invalid_email"
    DUPLICATE_IN_FILE = "duplicate_in_file"
    ALREADY_INVITED = "already_invited"
    INSTITUTIONAL_EMAIL = "institutional_email"
    EXPIRY_OUT_OF_RANGE = "expiry_out_of_range"


_MESSAGES = {
    RowResult.INVALID_EMAIL: "El correo no es válido.",
    RowResult.DUPLICATE_IN_FILE: "El correo ya aparece en una fila anterior del archivo.",
    RowResult.ALREADY_INVITED: "Esa persona ya tiene una invitación vigente.",
    RowResult.INSTITUTIONAL_EMAIL: "Es un correo de Unilibre: ingresa con su cuenta institucional.",
}


@dataclass(frozen=True)
class BatchRowInput:
    line: int
    email: str
    name: str | None = None
    access_expires_at: datetime | None = None
    invalid_expiry: bool = False  # `vence` no es una fecha AAAA-MM-DD


@dataclass(frozen=True)
class BatchRow:
    line: int
    email: str
    result: RowResult
    name: str | None = None
    access_expires_at: datetime | None = None
    message: str | None = None


def _end_of_day(day: date) -> datetime:
    return datetime.combine(day, time(23, 59, 59), tzinfo=COLOMBIA).astimezone(COLOMBIA)


def parse_csv(content: str) -> list[BatchRowInput]:
    """Lee el archivo; un encabezado distinto lanza `InvalidBatchFileError`."""
    rows = list(csv.reader(io.StringIO(content.lstrip("﻿"))))
    if not rows or [cell.strip().lower() for cell in rows[0]] != CSV_HEADER:
        raise InvalidBatchFileError(f"El encabezado debe ser exactamente: {','.join(CSV_HEADER)}.")
    parsed: list[BatchRowInput] = []
    for number, cells in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in cells):
            continue
        cells = [*cells, "", ""][:3]
        email, name, expiry = (cell.strip() for cell in cells)
        access_expires_at: datetime | None = None
        invalid_expiry = False
        if expiry:
            try:
                access_expires_at = _end_of_day(date.fromisoformat(expiry))
            except ValueError:
                invalid_expiry = True
        parsed.append(
            BatchRowInput(
                line=number,
                email=email,
                name=name or None,
                access_expires_at=access_expires_at,
                invalid_expiry=invalid_expiry,
            )
        )
        if len(parsed) > BATCH_MAX_ROWS:
            raise BatchTooLargeError(f"El lote admite hasta {BATCH_MAX_ROWS} filas.")
    return parsed


@dataclass(eq=False)
class InvitationBatch:
    created_by: UUID
    status: BatchStatus
    rows: list[BatchRow]
    expires_at: datetime
    created_at: datetime
    id: UUID | None = None
    confirmed_at: datetime | None = None

    @property
    def valid_count(self) -> int:
        return sum(1 for row in self.rows if row.result is RowResult.VALID)

    @property
    def invalid_count(self) -> int:
        return len(self.rows) - self.valid_count

    def valid_rows(self) -> list[BatchRow]:
        return [row for row in self.rows if row.result is RowResult.VALID]

    @classmethod
    def validate(
        cls,
        rows: Sequence[BatchRowInput],
        *,
        created_by: UUID,
        is_admin: bool,
        existing_emails: Iterable[str],
        institutional_domains: Sequence[str],
        settings: IdentitySettings,
        now: datetime,
        default_access_expires_at: datetime | None,
    ) -> "InvitationBatch":
        if len(rows) > BATCH_MAX_ROWS:
            raise BatchTooLargeError(f"El lote admite hasta {BATCH_MAX_ROWS} filas.")
        existing = {email.strip().lower() for email in existing_emails}
        seen: set[str] = set()
        default = default_access_expires_at or now + settings.default_guest_access
        results: list[BatchRow] = []
        for item in rows:
            email = item.email.strip()
            key = email.lower()
            expires = item.access_expires_at or default
            base = BatchRow(
                line=item.line,
                email=email,
                result=RowResult.VALID,
                name=(item.name or "").strip() or None,
                access_expires_at=expires,
            )
            result = _check(
                item,
                email,
                key,
                expires,
                seen,
                existing,
                institutional_domains,
                now=now,
                is_admin=is_admin,
                settings=settings,
            )
            seen.add(key)
            results.append(
                base if result is None else replace(base, result=result[0], message=result[1])
            )
        return cls(
            created_by=created_by,
            status=BatchStatus.PENDING_CONFIRMATION,
            rows=results,
            expires_at=now + BATCH_TTL,
            created_at=now,
        )

    def reject_row(self, line: int, result: RowResult, message: str | None = None) -> None:
        """Al confirmar, una fila válida puede dejar de serlo (por ejemplo, otra invitación al
        mismo correo se creó entre la validación y la confirmación)."""
        self.rows = [
            replace(row, result=result, message=message or _MESSAGES.get(result))
            if row.line == line
            else row
            for row in self.rows
        ]

    def confirm(self, now: datetime) -> None:
        if self.status is not BatchStatus.PENDING_CONFIRMATION or now >= self.expires_at:
            raise BatchNotPendingError("El lote ya fue confirmado o venció.")
        self.status = BatchStatus.CONFIRMED
        self.confirmed_at = now


def _check(
    item: BatchRowInput,
    email: str,
    key: str,
    expires: datetime,
    seen: set[str],
    existing: set[str],
    domains: Sequence[str],
    *,
    now: datetime,
    is_admin: bool,
    settings: IdentitySettings,
) -> tuple[RowResult, str] | None:
    def fail(result: RowResult, message: str | None = None) -> tuple[RowResult, str]:
        return result, message or _MESSAGES[result]

    if len(email) > 254 or not _EMAIL.fullmatch(email):
        return fail(RowResult.INVALID_EMAIL)
    if key in seen:
        return fail(RowResult.DUPLICATE_IN_FILE)
    if is_institutional_email(email, domains):
        return fail(RowResult.INSTITUTIONAL_EMAIL)
    if key in existing:
        return fail(RowResult.ALREADY_INVITED)
    if item.invalid_expiry:
        return fail(RowResult.EXPIRY_OUT_OF_RANGE, "La fecha debe tener el formato AAAA-MM-DD.")
    try:
        validate_access_expiry(expires, now=now, is_admin=is_admin, settings=settings)
    except AccessExpiryOutOfRangeError as error:
        return fail(RowResult.EXPIRY_OUT_OF_RANGE, error.message)
    return None
