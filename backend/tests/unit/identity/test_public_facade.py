"""T110: fachada de `identity` para otros contextos (FR-012; research R-04).

Las ligas y la analítica de programa (specs futuras) excluyen a los invitados preguntando aquí,
sin importar nada interno de `identity`.
"""

from datetime import UTC, datetime
from uuid import uuid4

from saber_uli.identity.application.directory import IdentityDirectory
from saber_uli.identity.application.public import UserDirectory
from saber_uli.identity.domain.user import InstitutionalIdentity, User
from tests.unit.identity.fakes import FakeIdentityUnitOfWork

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


async def test_distingue_institucionales_e_invitados() -> None:
    uow = FakeIdentityUnitOfWork()
    student = await uow.users.add(
        User.new_institutional(
            InstitutionalIdentity(tenant_id=uuid4(), object_id=uuid4()),
            email="ana@unilibre.edu.co",
            display_name="Ana",
            now=T0,
        )
    )
    guest = await uow.users.add(User.new_guest(email="laura@correo.co", display_name=None, now=T0))
    directory: UserDirectory = IdentityDirectory(uow_factory=uow)
    assert student.id is not None and guest.id is not None

    assert await directory.is_institutional(student.id) is True
    assert await directory.is_guest(student.id) is False
    assert await directory.is_institutional(guest.id) is False
    assert await directory.is_guest(guest.id) is True


async def test_un_usuario_desconocido_no_es_ni_uno_ni_otro() -> None:
    directory = IdentityDirectory(uow_factory=FakeIdentityUnitOfWork())
    unknown = uuid4()

    assert await directory.is_institutional(unknown) is False
    assert await directory.is_guest(unknown) is False
