"""Permisos por rol (FR-023, FR-026, FR-030; research R-22; contrato: esquema `Permission`).

Los permisos dicen qué funciones puede usar un rol. El alcance (invitaciones propias, grupos
propios, programas asignados) lo verifica la capa de aplicación: fuera de alcance responde 404 y
una función no permitida, 403.
"""

from collections.abc import Iterable, Mapping
from enum import StrEnum

from saber_uli.identity.domain.roles import Role


class Permission(StrEnum):
    INVITATIONS_MANAGE_OWN = "invitations:manage_own"
    INVITATIONS_MANAGE_ALL = "invitations:manage_all"
    USERS_MANAGE = "users:manage"
    GROUPS_MANAGE = "groups:manage"
    GROUPS_READ_OWN_STUDENTS = "groups:read_own_students"
    PROGRAMS_READ_AGGREGATED = "programs:read_aggregated"
    PROGRAMS_MANAGE = "programs:manage"
    SETTINGS_MANAGE = "settings:manage"
    AUDIT_READ = "audit:read"
    POLICY_PUBLISH = "policy:publish"
    DELETIONS_READ = "deletions:read"


ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.STUDENT: frozenset(),
    Role.GUEST: frozenset(),
    Role.TEACHER: frozenset(
        {Permission.INVITATIONS_MANAGE_OWN, Permission.GROUPS_READ_OWN_STUDENTS}
    ),
    # FR-026: solo datos agregados o seudonimizados de sus programas.
    Role.PROGRAM_DIRECTOR: frozenset({Permission.PROGRAMS_READ_AGGREGATED}),
    Role.ADMIN: frozenset(Permission),
}


def permissions_for(roles: Iterable[Role | str]) -> frozenset[Permission]:
    """Unión de los permisos de los roles (FR-023). Un rol desconocido lanza `ValueError`."""
    granted: frozenset[Permission] = frozenset()
    for role in roles:
        granted |= ROLE_PERMISSIONS[Role(role)]
    return granted
