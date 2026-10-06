"""T044: la fábrica de usuarios de prueba crea cuentas válidas por rol."""

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import UserKind, UserStatus
from tests.integration.conftest import UserFactory


async def test_fabrica_por_rol(user_factory: UserFactory) -> None:
    student = await user_factory()
    staff = await user_factory(Role.TEACHER, Role.ADMIN)
    guest = await user_factory(Role.GUEST)
    disabled = await user_factory(status_disabled=True)

    assert student.roles == {Role.STUDENT}
    assert staff.roles == {Role.STUDENT, Role.TEACHER, Role.ADMIN}
    assert guest.kind is UserKind.GUEST
    assert guest.roles == {Role.GUEST}
    assert disabled.status is UserStatus.DISABLED
    assert len({u.id for u in (student, staff, guest, disabled)}) == 4
