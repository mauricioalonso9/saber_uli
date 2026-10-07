"""Versiones de la política de tratamiento de datos (data-model §2.10; FR-016, FR-017).

Una versión publicada es inmutable. La vigente es la de mayor `effective_from` que ya empezó a
regir; publicar una nueva exige que todos vuelvan a autorizar (FR-017).
"""

import re
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+")
TITLE_MAX_LENGTH = 200
BODY_MIN_LENGTH = 200
BODY_MAX_LENGTH = 100_000


class InvalidPolicyVersionError(RuleViolationError):
    slug = "invalid-policy-version"


class PolicyVersionExistsError(ConflictError):
    slug = "policy-version-exists"


class EffectiveFromTooEarlyError(RuleViolationError):
    slug = "effective-from-too-early"


@dataclass(frozen=True)
class PolicyVersion:
    id: UUID | None
    version: str
    title: str
    body_markdown: str
    effective_from: datetime
    published_by: UUID | None

    @classmethod
    def publish(
        cls,
        *,
        version: str,
        title: str,
        body_markdown: str,
        effective_from: datetime,
        published_by: UUID,
        existing_versions: Collection[str],
        latest_effective_from: datetime | None,
    ) -> "PolicyVersion":
        if not VERSION_PATTERN.fullmatch(version):
            raise InvalidPolicyVersionError(
                "La versión debe tener el formato número.número, por ejemplo 2.0."
            )
        if not title.strip() or len(title) > TITLE_MAX_LENGTH:
            raise InvalidPolicyVersionError(
                f"El título es obligatorio y admite hasta {TITLE_MAX_LENGTH} caracteres."
            )
        if not BODY_MIN_LENGTH <= len(body_markdown) <= BODY_MAX_LENGTH:
            raise InvalidPolicyVersionError(
                f"El texto debe tener entre {BODY_MIN_LENGTH} y {BODY_MAX_LENGTH} caracteres."
            )
        if version in existing_versions:
            raise PolicyVersionExistsError(f"La versión {version} ya fue publicada.")
        # La vigente es la de mayor `effective_from`: una fecha igual la volvería ambigua y una
        # anterior haría que la versión nueva nunca rigiera.
        if latest_effective_from is not None and effective_from <= latest_effective_from:
            raise EffectiveFromTooEarlyError(
                "La fecha de vigencia debe ser posterior a la de la última versión publicada."
            )
        return cls(
            id=None,
            version=version,
            title=title,
            body_markdown=body_markdown,
            effective_from=effective_from,
            published_by=published_by,
        )
