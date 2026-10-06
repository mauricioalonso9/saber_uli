"""Roles de la plataforma (FR-023; contrato: esquema `Role`)."""

from collections.abc import Iterable
from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    GUEST = "guest"
    TEACHER = "teacher"
    PROGRAM_DIRECTOR = "program_director"
    ADMIN = "admin"


# Roles con funciones privilegiadas: exigen la sesión privilegiada de R-15 (claim `priv`).
PRIVILEGED_ROLES = frozenset({Role.TEACHER, Role.PROGRAM_DIRECTOR, Role.ADMIN})


def has_privileged_role(roles: Iterable[Role | str]) -> bool:
    return any(Role(role) in PRIVILEGED_ROLES for role in roles)
