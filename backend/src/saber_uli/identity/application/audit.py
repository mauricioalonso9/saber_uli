"""Auditoría (FR-035, SC-004; research R-24; data-model §2.14 y §5).

`record_audit` escribe el evento con la misma unidad de trabajo que la acción: se confirma o se
revierte junto con ella. `details` solo admite identificadores y valores no personales (por
ejemplo, roles antes y después o fechas); una clave de nombre o correo, o cualquier valor con
forma de correo, lanza `PersonalDataInAuditError` antes de escribir.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork


class AuditAction(StrEnum):
    """Catálogo cerrado de data-model §5."""

    USER_CREATED = "user.created"
    USER_ROLE_GRANTED = "user.role_granted"
    USER_ROLE_REVOKED = "user.role_revoked"
    USER_DIRECTOR_PROGRAMS_CHANGED = "user.director_programs_changed"
    USER_DISABLED = "user.disabled"
    USER_REACTIVATED = "user.reactivated"
    USER_ERASED = "user.erased"
    INVITATION_CREATED = "invitation.created"
    INVITATION_RESENT = "invitation.resent"
    INVITATION_EXPIRY_CHANGED = "invitation.expiry_changed"
    INVITATION_REVOKED = "invitation.revoked"
    INVITATION_ACCEPTED = "invitation.accepted"
    INVITATION_BATCH_CONFIRMED = "invitation_batch.confirmed"
    GROUP_CREATED = "group.created"
    GROUP_UPDATED = "group.updated"
    GROUP_ARCHIVED = "group.archived"
    GROUP_MEMBER_ADDED = "group.member_added"
    GROUP_MEMBER_REMOVED = "group.member_removed"
    GROUP_TEACHER_ADDED = "group.teacher_added"
    GROUP_TEACHER_REMOVED = "group.teacher_removed"
    PROGRAM_CREATED = "program.created"
    PROGRAM_UPDATED = "program.updated"
    POLICY_PUBLISHED = "policy.published"
    CONSENT_ACCEPTED = "consent.accepted"
    CONSENT_REJECTED = "consent.rejected"
    CONSENT_REVOKED = "consent.revoked"
    DELETION_REQUESTED = "deletion.requested"
    DELETION_COMPLETED = "deletion.completed"
    RETENTION_NOTICE_SENT = "retention.notice_sent"
    RETENTION_SKIPPED_LAST_ADMIN = "retention.skipped_last_admin"
    INVITATION_CONTACT_PURGED = "invitation.contact_purged"
    SETTING_CHANGED = "setting.changed"
    SESSION_REUSE_DETECTED = "session.reuse_detected"
    AUTH_LOGIN_REJECTED = "auth.login_rejected"


class AuditTarget(StrEnum):
    USER = "user"
    INVITATION = "invitation"
    GROUP = "group"
    PROGRAM = "program"
    POLICY = "policy"
    SETTING = "setting"
    DELETION_REQUEST = "deletion_request"
    SESSION = "session"


class PersonalDataInAuditError(ValueError):
    """`details` contiene (o parece contener) datos personales."""


@dataclass(frozen=True)
class AuditEntry:
    action: AuditAction
    target: AuditTarget
    occurred_at: datetime
    target_id: UUID | None = None
    subject_user_id: UUID | None = None
    actor_id: UUID | None = None  # None = sistema (tareas programadas, CLI)
    details: Mapping[str, Any] = field(default_factory=dict)


_PERSONAL_KEYS = frozenset(
    {"name", "nombre", "display_name", "given_name", "family_name", "preferred_username"}
)
_PERSONAL_KEY_FRAGMENTS = ("email", "correo")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")


def _check(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _PERSONAL_KEYS or any(
                f in normalized for f in _PERSONAL_KEY_FRAGMENTS
            ):
                raise PersonalDataInAuditError(f"clave no permitida en la auditoría: {key!r}")
            _check(nested)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            _check(item)
    elif isinstance(value, str) and _EMAIL.search(value):
        raise PersonalDataInAuditError("un valor de la auditoría tiene forma de correo")


async def record_audit(
    uow: IdentityUnitOfWork,
    action: AuditAction,
    *,
    target: AuditTarget,
    now: datetime,
    target_id: UUID | None = None,
    subject_user_id: UUID | None = None,
    actor_id: UUID | None = None,
    details: Mapping[str, Any] | None = None,
) -> None:
    payload = dict(details or {})
    _check(payload)
    await uow.audit.add(
        AuditEntry(
            action=AuditAction(action),
            target=AuditTarget(target),
            occurred_at=now,
            target_id=target_id,
            subject_user_id=subject_user_id,
            actor_id=actor_id,
            details=payload,
        )
    )
