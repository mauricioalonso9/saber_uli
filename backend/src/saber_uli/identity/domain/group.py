"""Grupos o cohortes (FR-027; data-model §2.6).

Los miembros son estudiantes institucionales (un invitado no entra en un grupo institucional,
escenario 6.5) y los docentes tienen el rol Docente. Un grupo archivado se conserva para el
historial.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import User, UserKind
from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

NAME_MIN, NAME_MAX = 2, 120
COHORT_MAX = 20
DESCRIPTION_MAX = 500


class InvalidGroupError(RuleViolationError):
    slug = "validation-error"


class NotInstitutionalStudentError(ConflictError):
    slug = "not-institutional-student"


class NotATeacherError(ConflictError):
    slug = "not-a-teacher"


_UNSET = object()


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not NAME_MIN <= len(cleaned) <= NAME_MAX:
        raise InvalidGroupError(f"El nombre debe tener entre {NAME_MIN} y {NAME_MAX} caracteres.")
    return cleaned


def _clean_optional(value: str | None, maximum: int, field: str) -> str | None:
    cleaned = (value or "").strip() or None
    if cleaned is not None and len(cleaned) > maximum:
        raise InvalidGroupError(f"{field} admite hasta {maximum} caracteres.")
    return cleaned


@dataclass(eq=False)
class Group:
    name: str
    created_by: UUID
    created_at: datetime
    id: UUID | None = None
    description: str | None = None
    cohort_label: str | None = None
    program_id: UUID | None = None
    archived_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        created_by: UUID,
        now: datetime,
        description: str | None = None,
        cohort_label: str | None = None,
        program_id: UUID | None = None,
    ) -> "Group":
        return cls(
            name=_clean_name(name),
            created_by=created_by,
            created_at=now,
            description=_clean_optional(description, DESCRIPTION_MAX, "La descripción"),
            cohort_label=_clean_optional(cohort_label, COHORT_MAX, "La cohorte"),
            program_id=program_id,
        )

    def update(
        self,
        *,
        now: datetime,
        name: str | None = None,
        description: object = _UNSET,
        cohort_label: object = _UNSET,
        archived: bool | None = None,
    ) -> None:
        """Solo cambia lo indicado; `description` y `cohort_label` admiten `None` para borrar."""
        if name is not None:
            self.name = _clean_name(name)
        if description is not _UNSET:
            self.description = _clean_optional(
                description if isinstance(description, str) else None,
                DESCRIPTION_MAX,
                "La descripción",
            )
        if cohort_label is not _UNSET:
            self.cohort_label = _clean_optional(
                cohort_label if isinstance(cohort_label, str) else None, COHORT_MAX, "La cohorte"
            )
        if archived is not None:
            self.archived_at = (self.archived_at or now) if archived else None


def ensure_member(user: User) -> None:
    if user.kind is not UserKind.INSTITUTIONAL or Role.STUDENT not in user.roles:
        raise NotInstitutionalStudentError(
            "Solo los estudiantes con cuenta institucional pueden ser miembros de un grupo."
        )


def ensure_teacher(user: User) -> None:
    if Role.TEACHER not in user.roles:
        raise NotATeacherError("La persona seleccionada no tiene el rol Docente.")
