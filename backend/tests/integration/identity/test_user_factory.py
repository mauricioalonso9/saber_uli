"""T044: la fábrica de usuarios de prueba crea cuentas válidas por rol."""

from datetime import UTC, datetime

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import UserKind, UserStatus
from saber_uli.identity.infrastructure.tokens import AccessTokenCodec
from tests.integration.conftest import TokenIssuer, UserFactory


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


async def test_emisor_de_tokens(
    user_factory: UserFactory, issue_token: TokenIssuer, token_codec: AccessTokenCodec
) -> None:
    admin = await user_factory(Role.ADMIN)
    now = datetime.now(UTC)
    claims = token_codec.decode(await issue_token(admin, priv=True), now=now)

    assert claims.sub == admin.id
    assert claims.priv is True
    assert claims.roles == ("admin", "student")
    assert claims.epoch == admin.auth_epoch
