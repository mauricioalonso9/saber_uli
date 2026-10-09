"""T135: reglas de roles y de cuentas (FR-023 a FR-026, FR-029; data-model §2.3, §2.4 y §4.1)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from saber_uli.identity.application.admin_users import AdminUsersService, LastAdminError
from saber_uli.identity.domain.program import Program
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import (
    DirectorRequiresProgramsError,
    GuestRoleExclusiveError,
    InstitutionalIdentity,
    StudentRoleRequiredError,
    User,
    UserStatus,
)
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.domain.errors import ConflictError
from tests.unit.identity.fakes import FakeIdentityUnitOfWork

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
PROGRAM = UUID("00000000-0000-7000-8000-0000000000b1")


def institutional(*roles: Role) -> User:
    user = User.new_institutional(
        InstitutionalIdentity(tenant_id=uuid4(), object_id=uuid4()),
        email=f"p-{uuid4().hex[:6]}@unilibre.edu.co",
        display_name="Persona",
        now=T0,
    )
    for role in roles:
        user.grant_role(role)
    return user


# ---------------------------------------------------------------------------- dominio


def test_un_institucional_conserva_siempre_el_rol_estudiante() -> None:
    user = institutional(Role.TEACHER)

    with pytest.raises(StudentRoleRequiredError) as info:
        user.set_roles({Role.TEACHER}, director_program_ids=set())
    assert info.value.slug == "student-role-required"


@pytest.mark.parametrize(
    "roles", [{Role.STUDENT, Role.GUEST}, {Role.GUEST}], ids=["mezclado", "solo-invitado"]
)
def test_un_institucional_no_es_invitado(roles: set[Role]) -> None:
    with pytest.raises(GuestRoleExclusiveError):
        institutional().set_roles(roles, director_program_ids=set())


def test_un_invitado_no_tiene_otros_roles() -> None:
    guest = User.new_guest(email="laura@correo.co", display_name=None, now=T0)

    with pytest.raises(GuestRoleExclusiveError) as info:
        guest.set_roles({Role.GUEST, Role.TEACHER}, director_program_ids=set())
    assert info.value.slug == "guest-role-exclusive"


def test_el_director_exige_al_menos_un_programa() -> None:
    user = institutional()

    with pytest.raises(DirectorRequiresProgramsError) as info:
        user.set_roles({Role.STUDENT, Role.PROGRAM_DIRECTOR}, director_program_ids=set())
    assert info.value.slug == "director-requires-programs"
    assert isinstance(info.value, ConflictError)


def test_roles_combinados_con_la_union_de_permisos() -> None:
    user = institutional()

    user.set_roles(
        {Role.STUDENT, Role.TEACHER, Role.PROGRAM_DIRECTOR}, director_program_ids={PROGRAM}
    )

    assert user.roles == {Role.STUDENT, Role.TEACHER, Role.PROGRAM_DIRECTOR}
    assert user.director_program_ids == {PROGRAM}
    assert {p.value for p in user.permissions} == {
        "invitations:manage_own",
        "groups:read_own_students",
        "programs:read_aggregated",
    }


def test_al_dejar_de_ser_director_pierde_sus_programas() -> None:
    user = institutional()
    user.set_roles({Role.STUDENT, Role.PROGRAM_DIRECTOR}, director_program_ids={PROGRAM})

    user.set_roles({Role.STUDENT}, director_program_ids={PROGRAM})

    assert user.director_program_ids == set()


def test_retirar_un_rol_cierra_las_sesiones_y_asignar_no() -> None:
    user = institutional()
    epoch = user.auth_epoch

    user.set_roles({Role.STUDENT, Role.TEACHER}, director_program_ids=set())
    assert user.auth_epoch == epoch

    user.set_roles({Role.STUDENT}, director_program_ids=set())
    assert user.auth_epoch == epoch + 1


# ---------------------------------------------------------------------------- aplicación


@pytest.fixture
def uow() -> FakeIdentityUnitOfWork:
    return FakeIdentityUnitOfWork()


@pytest.fixture
def service(uow: FakeIdentityUnitOfWork) -> AdminUsersService:
    return AdminUsersService(uow_factory=uow, clock=FixedClock(T0))


async def saved(uow: FakeIdentityUnitOfWork, *roles: Role) -> UUID:
    user = await uow.users.add(institutional(*roles))
    assert user.id is not None
    return user.id


async def test_no_se_retira_el_rol_al_ultimo_administrador(
    service: AdminUsersService, uow: FakeIdentityUnitOfWork
) -> None:
    admin = await saved(uow, Role.ADMIN)

    with pytest.raises(LastAdminError) as info:
        await service.set_roles(admin, admin, {Role.STUDENT}, director_program_ids=set())
    assert info.value.slug == "last-admin"
    assert Role.ADMIN in (await uow.users.get(admin)).roles  # type: ignore[union-attr]


async def test_con_otro_administrador_activo_si_se_retira(
    service: AdminUsersService, uow: FakeIdentityUnitOfWork
) -> None:
    admin = await saved(uow, Role.ADMIN)
    other = await saved(uow, Role.ADMIN)

    view = await service.set_roles(admin, other, {Role.STUDENT}, director_program_ids=set())

    assert view.user.roles == {Role.STUDENT}


async def test_no_se_desactiva_al_ultimo_administrador(
    service: AdminUsersService, uow: FakeIdentityUnitOfWork
) -> None:
    admin = await saved(uow, Role.ADMIN)

    with pytest.raises(LastAdminError):
        await service.set_status(admin, admin, "disabled")


async def test_desactivar_cierra_las_sesiones_y_reactivar_no_las_devuelve(
    service: AdminUsersService, uow: FakeIdentityUnitOfWork
) -> None:
    admin = await saved(uow, Role.ADMIN)
    student = await saved(uow)
    epoch = (await uow.users.get(student)).auth_epoch  # type: ignore[union-attr]

    disabled = await service.set_status(admin, student, "disabled")
    reactivated = await service.set_status(admin, student, "active")

    assert disabled.status == "disabled"
    assert reactivated.status == "active"
    assert reactivated.user.status is UserStatus.ACTIVE
    assert reactivated.user.auth_epoch == epoch + 1
    actions = [entry.action.value for entry in uow.audit.entries]
    assert actions == ["user.disabled", "user.reactivated"]


async def test_cambiar_roles_audita_antes_y_despues_y_los_programas(
    service: AdminUsersService, uow: FakeIdentityUnitOfWork
) -> None:
    admin = await saved(uow, Role.ADMIN)
    teacher = await saved(uow, Role.TEACHER)
    program = await uow.programs.add(Program.new(code="DER-BOG", name="Derecho", campus="Bogotá"))
    assert program.id is not None

    await service.set_roles(
        admin,
        teacher,
        {Role.STUDENT, Role.PROGRAM_DIRECTOR},
        director_program_ids={program.id},
    )

    entries = {entry.action.value: entry for entry in uow.audit.entries}
    granted = entries["user.role_granted"]
    revoked = entries["user.role_revoked"]
    assert granted.details["roles"] == ["program_director"]
    assert revoked.details["roles"] == ["teacher"]
    assert granted.details["before"] == ["student", "teacher"]
    assert granted.details["after"] == ["program_director", "student"]
    assert entries["user.director_programs_changed"].details["program_ids"] == [str(program.id)]
    assert all(entry.actor_id == admin for entry in uow.audit.entries)


async def test_un_programa_inexistente_no_se_asigna(
    service: AdminUsersService, uow: FakeIdentityUnitOfWork
) -> None:
    admin = await saved(uow, Role.ADMIN)
    student = await saved(uow)

    with pytest.raises(ConflictError):
        await service.set_roles(
            admin, student, {Role.STUDENT, Role.PROGRAM_DIRECTOR}, director_program_ids={uuid4()}
        )
