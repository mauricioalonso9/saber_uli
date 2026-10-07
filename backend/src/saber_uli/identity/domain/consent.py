"""Autorización de tratamiento de datos (data-model §2.11; FR-014 a FR-018).

La autorización está vigente solo si el último registro del usuario es `accepted` y corresponde
a la versión vigente de la política. Sin registros, con `rejected`, con `revoked`, con una versión
anterior o sin ninguna política publicada, se exige autorizar (`consent_required`).

La persona decide (`accepted` o `rejected`) solo sobre la versión vigente y revoca solo una
autorización vigente; la revocación es un registro más, nunca un borrado (Ley 1581, art. 9).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

WEB_PWA_CHANNEL = "web_pwa"


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
    channel: str = WEB_PWA_CHANNEL


class InvalidConsentDecisionError(RuleViolationError):
    slug = "invalid-consent-decision"


class PolicyVersionNotCurrentError(ConflictError):
    slug = "policy-version-not-current"


class NoActiveConsentError(ConflictError):
    slug = "no-active-consent"


def consent_is_current(
    latest: ConsentRecord | None, *, current_policy_version_id: UUID | None
) -> bool:
    return (
        latest is not None
        and current_policy_version_id is not None
        and latest.decision is ConsentDecision.ACCEPTED
        and latest.policy_version_id == current_policy_version_id
    )


def decide_consent(
    decision: ConsentDecision,
    *,
    policy_version_id: UUID,
    current_policy_version_id: UUID | None,
    now: datetime,
) -> ConsentRecord:
    if decision is ConsentDecision.REVOKED:
        raise InvalidConsentDecisionError("La decisión debe ser aceptar o no aceptar.")
    if current_policy_version_id is None or policy_version_id != current_policy_version_id:
        raise PolicyVersionNotCurrentError(
            "La versión de la política ya no es la vigente; lea la versión actual."
        )
    return ConsentRecord(policy_version_id=policy_version_id, decision=decision, decided_at=now)


def revoke_consent(
    latest: ConsentRecord | None, *, current_policy_version_id: UUID | None, now: datetime
) -> ConsentRecord:
    if latest is None or not consent_is_current(
        latest, current_policy_version_id=current_policy_version_id
    ):
        raise NoActiveConsentError("No hay una autorización vigente para revocar.")
    return ConsentRecord(
        policy_version_id=latest.policy_version_id,
        decision=ConsentDecision.REVOKED,
        decided_at=now,
    )
