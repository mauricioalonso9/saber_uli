"""Programas académicos del catálogo (data-model §2.5; contrato `ProgramInput`).

Los inactivos no aparecen al completar el perfil. El código institucional (por ejemplo
`DER-BOG`) identifica al programa en las cargas masivas.
"""

import re
from dataclasses import dataclass
from uuid import UUID

from saber_uli.shared.domain.errors import RuleViolationError

CODE_PATTERN = re.compile(r"[A-Z0-9-]{2,20}")
NAME_MIN, NAME_MAX = 3, 200
CAMPUS_MIN, CAMPUS_MAX = 2, 100


class InvalidProgramError(RuleViolationError):
    slug = "invalid-program"


def _validate(code: str, name: str, campus: str) -> None:
    if not CODE_PATTERN.fullmatch(code):
        raise InvalidProgramError(
            "El código debe tener de 2 a 20 letras mayúsculas, números o guiones."
        )
    if not NAME_MIN <= len(name) <= NAME_MAX:
        raise InvalidProgramError(f"El nombre debe tener entre {NAME_MIN} y {NAME_MAX} caracteres.")
    if not CAMPUS_MIN <= len(campus) <= CAMPUS_MAX:
        raise InvalidProgramError(
            f"La seccional debe tener entre {CAMPUS_MIN} y {CAMPUS_MAX} caracteres."
        )


@dataclass
class Program:
    id: UUID | None
    code: str
    name: str
    campus: str
    active: bool = True

    @classmethod
    def new(cls, *, code: str, name: str, campus: str, active: bool = True) -> "Program":
        code, name, campus = code.strip(), name.strip(), campus.strip()
        _validate(code, name, campus)
        return cls(id=None, code=code, name=name, campus=campus, active=active)

    def describe(self, *, name: str, campus: str) -> bool:
        """Cambia nombre y seccional; devuelve si algo cambió."""
        name, campus = name.strip(), campus.strip()
        _validate(self.code, name, campus)
        changed = (name, campus) != (self.name, self.campus)
        self.name, self.campus = name, campus
        return changed
