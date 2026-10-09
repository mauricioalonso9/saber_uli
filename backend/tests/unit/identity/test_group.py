"""T138: reglas de grupos (FR-027; data-model §2.6)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from saber_uli.identity.domain.group import (
    Group,
    InvalidGroupError,
    NotATeacherError,
    NotInstitutionalStudentError,
    ensure_member,
    ensure_teacher,
)
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import InstitutionalIdentity, User
from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
ADMIN = uuid4()


def new_group(**overrides: object) -> Group:
    values: dict[str, object] = {"name": "Derecho 2026-2", "created_by": ADMIN, "now": T0}
    values.update(overrides)
    return Group.create(**values)  # type: ignore[arg-type]


def institutional(*roles: Role) -> User:
    user = User.new_institutional(
        InstitutionalIdentity(tenant_id=uuid4(), object_id=uuid4()),
        email="ana@unilibre.edu.co",
        display_name="Ana",
        now=T0,
    )
    for role in roles:
        user.grant_role(role)
    return user


def test_un_grupo_nuevo() -> None:
    group = new_group(name="  Derecho 2026-2 ", cohort_label="2026-2", description="Cohorte")

    assert (group.name, group.cohort_label, group.description) == (
        "Derecho 2026-2",
        "2026-2",
        "Cohorte",
    )
    assert group.archived_at is None
    assert group.created_at == T0


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "D"},
        {"name": "x" * 121},
        {"cohort_label": "x" * 21},
        {"description": "x" * 501},
    ],
    ids=["nombre-corto", "nombre-largo", "cohorte", "descripcion"],
)
def test_limites_de_los_campos(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidGroupError) as info:
        new_group(**overrides)
    assert isinstance(info.value, RuleViolationError)


def test_editar_y_archivar() -> None:
    group = new_group()

    group.update(name="Derecho 2027-1", cohort_label=None, archived=True, now=T0)

    assert group.name == "Derecho 2027-1"
    assert group.cohort_label is None
    assert group.archived_at == T0
    group.update(archived=False, now=T0)
    assert group.archived_at is None


def test_los_miembros_son_estudiantes_institucionales() -> None:
    ensure_member(institutional())
    guest = User.new_guest(email="laura@correo.co", display_name=None, now=T0)

    with pytest.raises(NotInstitutionalStudentError) as info:
        ensure_member(guest)
    assert info.value.slug == "not-institutional-student"
    assert isinstance(info.value, ConflictError)


def test_los_docentes_tienen_el_rol_docente() -> None:
    ensure_teacher(institutional(Role.TEACHER))

    with pytest.raises(NotATeacherError) as info:
        ensure_teacher(institutional())
    assert info.value.slug == "not-a-teacher"
