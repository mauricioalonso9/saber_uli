"""T039: matriz de permisos por rol (FR-023, FR-026, FR-030; research R-22)."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from saber_uli.identity.domain.permissions import Permission, permissions_for
from saber_uli.identity.domain.roles import Role, has_privileged_role

REPO_ROOT = Path(__file__).parents[4]
CONTRACT = REPO_ROOT / "specs" / "001-identidad-acceso" / "contracts" / "openapi.yaml"


def contract_enum(schema: str) -> set[str]:
    spec: dict[str, Any] = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return set(spec["components"]["schemas"][schema]["enum"])


def test_los_roles_coinciden_con_el_contrato() -> None:
    assert {r.value for r in Role} == contract_enum("Role")


def test_los_permisos_coinciden_con_el_contrato() -> None:
    assert {p.value for p in Permission} == contract_enum("Permission")


@pytest.mark.parametrize("role", [Role.STUDENT, Role.GUEST])
def test_estudiante_e_invitado_no_tienen_permisos_de_gestion(role: Role) -> None:
    assert permissions_for([role]) == frozenset()


def test_docente_gestiona_sus_invitaciones_y_ve_a_sus_estudiantes() -> None:
    assert permissions_for([Role.TEACHER]) == {
        Permission.INVITATIONS_MANAGE_OWN,
        Permission.GROUPS_READ_OWN_STUDENTS,
    }


def test_director_solo_ve_datos_agregados_de_sus_programas() -> None:
    # FR-026: ningún permiso que exponga nombre, correo u otro dato de un estudiante.
    assert permissions_for([Role.PROGRAM_DIRECTOR]) == {Permission.PROGRAMS_READ_AGGREGATED}


def test_administrador_tiene_todos_los_permisos() -> None:
    assert permissions_for([Role.ADMIN]) == frozenset(Permission)


@pytest.mark.parametrize(
    "permission",
    [
        Permission.INVITATIONS_MANAGE_ALL,
        Permission.USERS_MANAGE,
        Permission.GROUPS_MANAGE,
        Permission.PROGRAMS_MANAGE,
        Permission.SETTINGS_MANAGE,
        Permission.AUDIT_READ,
        Permission.POLICY_PUBLISH,
        Permission.DELETIONS_READ,
    ],
)
def test_los_permisos_de_administracion_son_exclusivos_del_administrador(
    permission: Permission,
) -> None:
    for role in Role:
        assert (permission in permissions_for([role])) == (role is Role.ADMIN)


def test_varios_roles_suman_sus_permisos() -> None:
    # FR-023: un usuario institucional con varios roles tiene la unión de permisos.
    assert permissions_for([Role.STUDENT, Role.TEACHER, Role.PROGRAM_DIRECTOR]) == {
        Permission.INVITATIONS_MANAGE_OWN,
        Permission.GROUPS_READ_OWN_STUDENTS,
        Permission.PROGRAMS_READ_AGGREGATED,
    }


def test_sin_roles_no_hay_permisos() -> None:
    assert permissions_for([]) == frozenset()


def test_acepta_roles_como_texto_del_contrato() -> None:
    assert permissions_for(["teacher"]) == permissions_for([Role.TEACHER])


def test_un_rol_desconocido_es_un_error() -> None:
    with pytest.raises(ValueError):
        permissions_for(["superuser"])


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        ([], False),
        ([Role.STUDENT], False),
        ([Role.GUEST], False),
        ([Role.TEACHER], True),
        ([Role.PROGRAM_DIRECTOR], True),
        ([Role.ADMIN], True),
        ([Role.STUDENT, Role.TEACHER], True),
    ],
)
def test_roles_privilegiados_para_la_sesion_privilegiada(roles: list[Role], expected: bool) -> None:
    # R-15: docente, director y administrador usan funciones privilegiadas (claim `priv`).
    assert has_privileged_role(roles) is expected
