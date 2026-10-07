"""T071: ingreso con la cuenta institucional (FR-001 a FR-005; escenarios 1.1 a 1.3; R-11, R-12)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from saber_uli.identity.application.access_guard import AccountDisabledError
from saber_uli.identity.application.audit import AuditAction
from saber_uli.identity.application.authenticate_institutional_user import (
    AuthenticateInstitutionalUser,
    InstitutionalClaims,
    TenantNotAllowedError,
)
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import UserKind, UserStatus
from saber_uli.shared.domain.clock import FixedClock
from tests.unit.identity.fakes import FakeIdentityUnitOfWork

TENANT = UUID("11111111-1111-4111-8111-111111111111")
OTHER_TENANT = UUID("22222222-2222-4222-8222-222222222222")
OID = UUID("aaaaaaaa-0000-4000-8000-000000000001")
T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def claims(**overrides: object) -> InstitutionalClaims:
    values: dict[str, object] = {
        "tenant_id": TENANT,
        "object_id": OID,
        "name": "Ana Pérez",
        "email": "ana.perez@unilibre.edu.co",
    }
    values.update(overrides)
    return InstitutionalClaims(**values)  # type: ignore[arg-type]


@pytest.fixture
def uow() -> FakeIdentityUnitOfWork:
    return FakeIdentityUnitOfWork()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


@pytest.fixture
def authenticate(uow: FakeIdentityUnitOfWork, clock: FixedClock) -> AuthenticateInstitutionalUser:
    return AuthenticateInstitutionalUser(uow_factory=uow, clock=clock, tenant_id=TENANT)


async def test_el_primer_ingreso_crea_la_cuenta_institucional_de_estudiante(
    authenticate: AuthenticateInstitutionalUser, uow: FakeIdentityUnitOfWork
) -> None:
    result = await authenticate.execute(claims())

    user = result.user
    assert result.created is True
    assert user.id is not None
    assert user.kind is UserKind.INSTITUTIONAL
    assert user.status is UserStatus.ACTIVE
    assert user.roles == {Role.STUDENT}
    assert (user.display_name, user.email) == ("Ana Pérez", "ana.perez@unilibre.edu.co")
    assert user.last_login_at == T0
    assert uow.commits == 1


async def test_el_primer_ingreso_se_audita_sin_datos_personales(
    authenticate: AuthenticateInstitutionalUser, uow: FakeIdentityUnitOfWork
) -> None:
    result = await authenticate.execute(claims())

    [entry] = uow.audit.entries
    assert entry.action is AuditAction.USER_CREATED
    assert entry.target_id == entry.subject_user_id == result.user.id
    assert entry.actor_id is None
    assert "ana" not in repr(dict(entry.details)).lower()


async def test_un_ingreso_posterior_reutiliza_la_cuenta_y_actualiza_nombre_y_correo(
    authenticate: AuthenticateInstitutionalUser,
    uow: FakeIdentityUnitOfWork,
    clock: FixedClock,
) -> None:
    first = await authenticate.execute(claims())
    clock.advance(timedelta(days=3))

    second = await authenticate.execute(
        claims(name="Ana María Pérez", email="ana.m.perez@unilibre.edu.co")
    )

    assert second.created is False
    assert second.user.id == first.user.id
    assert len(uow.users.rows) == 1
    assert second.user.display_name == "Ana María Pérez"
    assert second.user.email == "ana.m.perez@unilibre.edu.co"
    assert second.user.last_login_at == T0 + timedelta(days=3)
    # user.created solo en el primer ingreso.
    assert [e.action for e in uow.audit.entries] == [AuditAction.USER_CREATED]


async def test_otro_inquilino_se_rechaza_sin_crear_cuenta(
    authenticate: AuthenticateInstitutionalUser, uow: FakeIdentityUnitOfWork
) -> None:
    with pytest.raises(TenantNotAllowedError) as info:
        await authenticate.execute(claims(tenant_id=OTHER_TENANT))

    assert info.value.code == "tenant_not_allowed"
    assert uow.users.rows == {}
    assert uow.commits == 0


async def test_una_cuenta_desactivada_no_ingresa(
    authenticate: AuthenticateInstitutionalUser, uow: FakeIdentityUnitOfWork
) -> None:
    result = await authenticate.execute(claims())
    result.user.disable()

    with pytest.raises(AccountDisabledError) as info:
        await authenticate.execute(claims())
    assert info.value.slug == "account-disabled"


async def test_sin_nombre_usa_el_correo_como_nombre_visible(
    authenticate: AuthenticateInstitutionalUser,
) -> None:
    result = await authenticate.execute(claims(name=None))

    assert result.user.display_name == "ana.perez@unilibre.edu.co"
