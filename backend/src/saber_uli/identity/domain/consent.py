"""Autorización de tratamiento de datos (data-model §2.11; FR-014 a FR-018).

La autorización está vigente solo si el último registro del usuario es `accepted` y corresponde
a la versión vigente de la política. Sin registros, con `rejected`, con `revoked`, con una versión
anterior o sin ninguna política publicada, se exige autorizar (`consent_required`).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ConsentDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVOKED = "revoked"


@dataclass(frozen=True)
class ConsentRecord:
    """Registro inmutable de una decisión (la tabla es de solo inserción)."""

    policy_version_id: UUID
    decision: ConsentDecision
    decided_at: datetime


def consent_is_current(
    latest: ConsentRecord | None, *, current_policy_version_id: UUID | None
) -> bool:
    return (
        latest is not None
        and current_policy_version_id is not None
        and latest.decision is ConsentDecision.ACCEPTED
        and latest.policy_version_id == current_policy_version_id
    )
