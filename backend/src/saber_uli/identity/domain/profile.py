"""Perfil del primer ingreso y su edición (FR-019 a FR-021; data-model §2.2).

- Institucional: programa académico (del catálogo, activo), semestre de 1 a 12, fecha estimada
  de presentación de Saber Pro y meta diaria. Nombre y correo vienen del directorio y no se
  editan aquí (FR-021).
- Invitado: nombre (de 2 a 120 caracteres), meta diaria y, si quiere, la fecha estimada; nunca
  programa ni semestre.

Cada actualización reemplaza el perfil completo con los datos de su tipo de cuenta.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

from saber_uli.identity.domain.user import UserKind
from saber_uli.shared.domain.errors import RuleViolationError

SEMESTER_MIN, SEMESTER_MAX = 1, 12
GUEST_NAME_MIN, GUEST_NAME_MAX = 2, 120


class DailyGoal(StrEnum):
    CASUAL = "casual"
    REGULAR = "regular"
    INTENSE = "intense"


class InvalidProfileError(RuleViolationError):
    slug = "invalid-profile"


class ProgramNotAvailableError(RuleViolationError):
    slug = "program-not-available"


@dataclass(frozen=True)
class ProgramRef:
    """Lo que el perfil necesita saber del programa elegido."""

    id: UUID
    active: bool


@dataclass(frozen=True)
class ProfileData:
    """Datos que envía la persona (contrato `ProfileUpdate`)."""

    daily_goal: DailyGoal
    program_id: UUID | None = None
    semester: int | None = None
    expected_exam_date: date | None = None
    guest_display_name: str | None = None


@dataclass
class Profile:
    user_id: UUID
    daily_goal: DailyGoal | None = None
    program_id: UUID | None = None
    semester: int | None = None
    expected_exam_date: date | None = None
    guest_display_name: str | None = None

    def is_complete(self, kind: UserKind) -> bool:
        if self.daily_goal is None:
            return False
        if kind is UserKind.GUEST:
            return self.guest_display_name is not None
        return (
            self.program_id is not None
            and self.semester is not None
            and self.expected_exam_date is not None
        )

    def update(self, kind: UserKind, data: ProfileData, *, program: ProgramRef | None) -> None:
        """Valida y aplica `data`. `program` es el programa de `data.program_id` (o `None`)."""
        if kind is UserKind.GUEST:
            self._update_guest(data)
        else:
            self._update_institutional(data, program)
        self.daily_goal = data.daily_goal
        self.expected_exam_date = data.expected_exam_date

    def _update_institutional(self, data: ProfileData, program: ProgramRef | None) -> None:
        if data.guest_display_name is not None:
            raise InvalidProfileError("El nombre institucional viene del directorio de Unilibre.")
        if data.program_id is None or data.semester is None or data.expected_exam_date is None:
            raise InvalidProfileError(
                "Indica tu programa, tu semestre y la fecha estimada de tu prueba Saber Pro."
            )
        if not SEMESTER_MIN <= data.semester <= SEMESTER_MAX:
            raise InvalidProfileError(
                f"El semestre debe estar entre {SEMESTER_MIN} y {SEMESTER_MAX}."
            )
        # Quien ya está en un programa que luego se desactivó puede conservarlo al editar.
        keeps_current = data.program_id == self.program_id
        if (
            program is None
            or program.id != data.program_id
            or not (program.active or keeps_current)
        ):
            raise ProgramNotAvailableError("El programa elegido no está disponible.")
        self.program_id = data.program_id
        self.semester = data.semester

    def _update_guest(self, data: ProfileData) -> None:
        if data.program_id is not None or data.semester is not None:
            raise InvalidProfileError("Los invitados no indican programa ni semestre.")
        name = (data.guest_display_name or "").strip()
        if not GUEST_NAME_MIN <= len(name) <= GUEST_NAME_MAX:
            raise InvalidProfileError(
                f"Tu nombre debe tener entre {GUEST_NAME_MIN} y {GUEST_NAME_MAX} caracteres."
            )
        self.guest_display_name = name
