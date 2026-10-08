"""T041: agregado `User` (data-model §2.1 y §4.1; FR-003, FR-005, FR-024, FR-029, FR-033; R-16)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from saber_uli.identity.domain.permissions import Permission
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import (
    GuestRoleExclusiveError,
    InstitutionalIdentity,
    InvalidUserTransitionError,
    StudentRoleRequiredError,
    User,
    UserKind,
    UserStatus,
)
from saber_uli.shared.domain.errors import ConflictError

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
IDENTITY = InstitutionalIdentity(
    tenant_id=UUID("11111111-1111-4111-8111-111111111111"),
    object_id=UUID("aaaaaaaa-0000-4000-8000-000000000001"),
)


def state(user: User) -> UserStatus:
    """Lee el estado sin que mypy lo estreche entre transiciones."""
    return user.status


def notice(user: User) -> datetime | None:
    return user.retention_notice_sent_at


def institutional() -> User:
    return User.new_institutional(
        IDENTITY, email="ana@unilibre.edu.co", display_name="Ana Pérez", now=NOW
    )


def guest() -> User:
    return User.new_guest(email="invitado@correo.co", display_name="Invitado", now=NOW)


# --- Creación ----------------------------------------------------------------------------------


def test_creacion_institucional_con_rol_estudiante() -> None:
    user = institutional()

    assert user.id is None  # lo asigna la base de datos (uuidv7) al guardar
    assert user.kind is UserKind.INSTITUTIONAL
    assert state(user) is UserStatus.ACTIVE
    assert user.roles == {Role.STUDENT}
    assert user.entra_identity == IDENTITY
    assert (user.email, user.display_name) == ("ana@unilibre.edu.co", "Ana Pérez")
    assert user.auth_epoch == 0
    assert user.created_at == NOW


def test_creacion_de_invitado_con_rol_invitado() -> None:
    user = guest()

    assert user.kind is UserKind.GUEST
    assert user.roles == {Role.GUEST}
    assert user.entra_identity is None


def test_los_permisos_son_la_union_de_los_roles() -> None:
    user = institutional()
    user.grant_role(Role.TEACHER)

    assert Permission.INVITATIONS_MANAGE_OWN in user.permissions
    assert user.has_privileged_role


# --- Transiciones de estado (§4.1) -----------------------------------------------------------


def test_desactivar_y_reactivar() -> None:
    user = institutional()

    user.disable()
    assert state(user) is UserStatus.DISABLED
    assert user.auth_epoch == 1  # revoca sesiones

    user.reactivate()
    assert state(user) is UserStatus.ACTIVE
    assert user.auth_epoch == 1  # reactivar no revoca nada


@pytest.mark.parametrize("start", ["active", "disabled"])
def test_solicitar_supresion_desde_activo_o_desactivado(start: str) -> None:
    user = institutional()
    if start == "disabled":
        user.disable()
    epoch = user.auth_epoch

    user.request_deletion()

    assert state(user) is UserStatus.DELETION_PENDING
    assert user.auth_epoch == epoch + 1


def test_la_lapida_no_tiene_datos_personales_ni_roles() -> None:
    user = institutional()
    user.director_program_ids = {uuid4()}
    user.request_deletion()

    user.to_tombstone()

    assert state(user) is UserStatus.DELETED
    assert (user.email, user.display_name) == (None, None)
    assert user.entra_identity is None
    assert user.roles == set()
    assert user.director_program_ids == set()


def test_solo_se_suprime_tras_la_solicitud() -> None:
    with pytest.raises(InvalidUserTransitionError):
        institutional().to_tombstone()


def test_deleted_es_final() -> None:
    user = institutional()
    user.request_deletion()
    user.to_tombstone()

    for transition in (user.disable, user.reactivate, user.request_deletion, user.to_tombstone):
        with pytest.raises(InvalidUserTransitionError):
            transition()
    with pytest.raises(InvalidUserTransitionError):
        user.record_login(NOW)


@pytest.mark.parametrize(
    ("prepare", "transition"),
    [
        ("disable", "disable"),
        (None, "reactivate"),
        ("request_deletion", "request_deletion"),
        ("request_deletion", "disable"),
        ("request_deletion", "reactivate"),
    ],
)
def test_transiciones_invalidas(prepare: str | None, transition: str) -> None:
    user = institutional()
    if prepare:
        getattr(user, prepare)()

    with pytest.raises(InvalidUserTransitionError) as info:
        getattr(user, transition)()
    assert isinstance(info.value, ConflictError)


def test_invalidar_sesiones_incrementa_la_epoca() -> None:
    user = institutional()

    user.invalidate_sessions()
    user.invalidate_sessions()

    assert user.auth_epoch == 2


# --- Ingreso (FR-005, FR-034c) -----------------------------------------------------------------


def test_registrar_ingreso_actualiza_datos_del_directorio_y_limpia_el_aviso() -> None:
    user = institutional()
    user.retention_notice_sent_at = NOW - timedelta(days=1)
    later = NOW + timedelta(days=200)

    user.record_login(later, email="ana.perez@unilibre.edu.co", display_name="Ana M. Pérez")

    assert user.last_login_at == later
    assert notice(user) is None
    assert (user.email, user.display_name) == ("ana.perez@unilibre.edu.co", "Ana M. Pérez")


def test_registrar_ingreso_sin_datos_nuevos_conserva_los_actuales() -> None:
    user = institutional()

    user.record_login(NOW)

    assert (user.email, user.display_name) == ("ana@unilibre.edu.co", "Ana Pérez")


@pytest.mark.parametrize("state", ["disabled", "deletion_pending"])
def test_no_se_registra_ingreso_si_la_cuenta_no_esta_activa(state: str) -> None:
    user = institutional()
    user.disable() if state == "disabled" else user.request_deletion()

    with pytest.raises(InvalidUserTransitionError):
        user.record_login(NOW)


# --- Roles (FR-023, FR-024) --------------------------------------------------------------------


def test_otorgar_un_rol_no_revoca_sesiones_y_retirarlo_si() -> None:
    user = institutional()

    user.grant_role(Role.ADMIN)
    assert user.roles == {Role.STUDENT, Role.ADMIN}
    assert user.auth_epoch == 0

    user.revoke_role(Role.ADMIN)
    assert user.roles == {Role.STUDENT}
    assert user.auth_epoch == 1


def test_otorgar_un_rol_existente_o_retirar_uno_ausente_no_cambia_nada() -> None:
    user = institutional()

    user.grant_role(Role.STUDENT)
    user.revoke_role(Role.TEACHER)

    assert user.roles == {Role.STUDENT}
    assert user.auth_epoch == 0


def test_el_invitado_no_tiene_otros_roles() -> None:
    with pytest.raises(GuestRoleExclusiveError) as info:
        guest().grant_role(Role.TEACHER)
    assert info.value.slug == "guest-role-exclusive"

    with pytest.raises(GuestRoleExclusiveError):
        institutional().grant_role(Role.GUEST)


def test_el_institucional_conserva_estudiante() -> None:
    with pytest.raises(StudentRoleRequiredError) as info:
        institutional().revoke_role(Role.STUDENT)
    assert info.value.slug == "student-role-required"


def test_la_lapida_no_recibe_roles() -> None:
    user = institutional()
    user.request_deletion()
    user.to_tombstone()

    with pytest.raises(InvalidUserTransitionError):
        user.grant_role(Role.TEACHER)
