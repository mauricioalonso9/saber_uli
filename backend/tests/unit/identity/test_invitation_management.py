"""T122: gestión de invitaciones (FR-006 a FR-010; escenarios 5.1, 5.3 a 5.5, 5.7 y 5.8;
data-model §2.7 y §4.2)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from saber_uli.identity.application.invitations import InvitationService, Inviter
from saber_uli.identity.domain.invitation import (
    AccessExpiryOutOfRangeError,
    GuestErasedError,
    InstitutionalEmailNotInvitableError,
    Invitation,
    InvitationAlreadyActiveError,
    InvitationNotFoundError,
    InvitationNotPendingError,
    InvitationNotRenewableError,
    InvitationStatus,
)
from saber_uli.identity.domain.user import User
from saber_uli.shared.domain.clock import FixedClock
from saber_uli.shared.domain.errors import ConflictError, NotFoundError, RuleViolationError
from tests.unit.identity.fakes import FakeIdentityUnitOfWork

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
TEACHER = Inviter(user_id=uuid4(), is_admin=False)
OTHER_TEACHER = Inviter(user_id=uuid4(), is_admin=False)
ADMIN = Inviter(user_id=uuid4(), is_admin=True)


@pytest.fixture
def uow() -> FakeIdentityUnitOfWork:
    return FakeIdentityUnitOfWork()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


@pytest.fixture
def service(uow: FakeIdentityUnitOfWork, clock: FixedClock) -> InvitationService:
    return InvitationService(
        uow_factory=uow, clock=clock, institutional_domains=["unilibre.edu.co"]
    )


def email() -> str:
    return f"invitado-{uuid4().hex[:6]}@correo.co"


async def accepted(
    service: InvitationService, uow: FakeIdentityUnitOfWork, *, days: int = 30
) -> tuple[Invitation, User]:
    """Invitación aceptada (el invitado ya ingresó una vez)."""
    invitation = await service.create(
        TEACHER, email=email(), access_expires_at=T0 + timedelta(days=days)
    )
    guest = await uow.users.add(invitation.new_guest_user(T0))
    assert guest.id is not None and invitation.id is not None
    invitation.accept(guest.id, T0)
    return invitation, guest


# ---------------------------------------------------------------------------- crear


@pytest.mark.parametrize("address", ["ana@unilibre.edu.co", "ana@est.unilibre.edu.co"])
async def test_un_correo_institucional_no_se_invita(
    service: InvitationService, address: str
) -> None:
    with pytest.raises(InstitutionalEmailNotInvitableError) as info:
        await service.create(TEACHER, email=address)
    assert isinstance(info.value, RuleViolationError)


async def test_sin_vencimiento_se_usa_el_plazo_por_defecto(service: InvitationService) -> None:
    invitation = await service.create(TEACHER, email=email())

    assert invitation.access_expires_at == T0 + timedelta(days=90)
    assert invitation.status is InvitationStatus.SENT
    assert invitation.invited_by == TEACHER.user_id


async def test_el_docente_no_supera_el_plazo_maximo(service: InvitationService) -> None:
    await service.create(TEACHER, email=email(), access_expires_at=T0 + timedelta(days=180))

    with pytest.raises(AccessExpiryOutOfRangeError) as info:
        await service.create(TEACHER, email=email(), access_expires_at=T0 + timedelta(days=181))
    assert "180" in info.value.message


async def test_el_administrador_no_tiene_plazo_maximo(service: InvitationService) -> None:
    invitation = await service.create(
        ADMIN, email=email(), access_expires_at=T0 + timedelta(days=400)
    )

    assert invitation.access_expires_at == T0 + timedelta(days=400)


async def test_el_vencimiento_debe_ser_futuro(service: InvitationService) -> None:
    with pytest.raises(AccessExpiryOutOfRangeError):
        await service.create(ADMIN, email=email(), access_expires_at=T0)


async def test_no_hay_dos_invitaciones_vigentes_al_mismo_correo(
    service: InvitationService,
) -> None:
    address = email()
    await service.create(TEACHER, email=address)

    with pytest.raises(InvitationAlreadyActiveError) as info:
        await service.create(ADMIN, email=address.upper())
    assert isinstance(info.value, ConflictError)


async def test_crear_queda_auditado(
    service: InvitationService, uow: FakeIdentityUnitOfWork
) -> None:
    invitation = await service.create(TEACHER, email=email())

    [entry] = uow.audit.entries
    assert entry.action.value == "invitation.created"
    assert (entry.actor_id, entry.target_id) == (TEACHER.user_id, invitation.id)


# ---------------------------------------------------------------------------- alcance


async def test_un_docente_no_ve_ni_gestiona_invitaciones_ajenas(
    service: InvitationService,
) -> None:
    invitation = await service.create(TEACHER, email=email())
    assert invitation.id is not None

    for action in (service.get, service.revoke, service.resend):
        with pytest.raises(InvitationNotFoundError) as info:
            await action(OTHER_TEACHER, invitation.id)
        assert isinstance(info.value, NotFoundError)
    assert (await service.get(ADMIN, invitation.id)).id == invitation.id


# ---------------------------------------------------------------------------- reenviar


async def test_reenviar_una_invitacion_sin_aceptar(
    service: InvitationService, clock: FixedClock
) -> None:
    invitation = await service.create(TEACHER, email=email())
    assert invitation.id is not None
    clock.advance(timedelta(days=8))  # el enlace de 7 días ya venció

    resent = await service.resend(TEACHER, invitation.id)

    assert resent.status is InvitationStatus.SENT
    assert resent.sent_at == T0 + timedelta(days=8)


async def test_no_se_reenvia_una_invitacion_aceptada(
    service: InvitationService, uow: FakeIdentityUnitOfWork
) -> None:
    invitation, _ = await accepted(service, uow)

    with pytest.raises(InvitationNotPendingError):
        await service.resend(TEACHER, invitation.id)


async def test_no_se_reenvia_una_invitacion_revocada(service: InvitationService) -> None:
    invitation = await service.create(TEACHER, email=email())
    assert invitation.id is not None
    await service.revoke(TEACHER, invitation.id)

    with pytest.raises(InvitationNotPendingError):
        await service.resend(TEACHER, invitation.id)


# ---------------------------------------------------------------------------- revocar


async def test_revocar_termina_el_acceso_del_invitado(
    service: InvitationService, uow: FakeIdentityUnitOfWork
) -> None:
    invitation, guest = await accepted(service, uow)
    epoch = guest.auth_epoch

    revoked = await service.revoke(ADMIN, invitation.id)

    assert revoked.status is InvitationStatus.REVOKED
    assert revoked.revoked_at == T0
    assert guest.auth_epoch == epoch + 1
    assert [e.action.value for e in uow.audit.entries][-1] == "invitation.revoked"


async def test_revocar_dos_veces_es_un_conflicto(service: InvitationService) -> None:
    invitation = await service.create(TEACHER, email=email())
    assert invitation.id is not None
    await service.revoke(TEACHER, invitation.id)

    with pytest.raises(ConflictError):
        await service.revoke(TEACHER, invitation.id)


# ---------------------------------------------------------------------------- vencimiento


async def test_ampliar_o_reducir_el_vencimiento_de_un_invitado_activo(
    service: InvitationService, uow: FakeIdentityUnitOfWork
) -> None:
    invitation, _ = await accepted(service, uow)

    changed = await service.change_expiry(TEACHER, invitation.id, T0 + timedelta(days=10))

    assert changed.access_expires_at == T0 + timedelta(days=10)
    assert changed.status is InvitationStatus.ACCEPTED
    assert [e.action.value for e in uow.audit.entries][-1] == "invitation.expiry_changed"


async def test_el_docente_no_amplia_mas_alla_del_maximo(
    service: InvitationService, uow: FakeIdentityUnitOfWork
) -> None:
    invitation, _ = await accepted(service, uow)

    with pytest.raises(AccessExpiryOutOfRangeError):
        await service.change_expiry(TEACHER, invitation.id, T0 + timedelta(days=181))


async def test_renovar_dentro_de_90_dias_vuelve_a_aceptada_y_limpia_el_aviso(
    service: InvitationService, uow: FakeIdentityUnitOfWork, clock: FixedClock
) -> None:
    invitation, guest = await accepted(service, uow, days=30)
    clock.advance(timedelta(days=30 + 89))  # venció hace 89 días
    guest.retention_notice_sent_at = clock.now() - timedelta(days=1)
    invitation.status = InvitationStatus.EXPIRED

    renewed = await service.change_expiry(ADMIN, invitation.id, clock.now() + timedelta(days=30))

    assert renewed.status is InvitationStatus.ACCEPTED
    assert renewed.revoked_at is None
    assert guest.retention_notice_sent_at is None


async def test_renovar_un_acceso_revocado_dentro_de_90_dias(
    service: InvitationService, uow: FakeIdentityUnitOfWork, clock: FixedClock
) -> None:
    invitation, _ = await accepted(service, uow)
    await service.revoke(ADMIN, invitation.id)
    clock.advance(timedelta(days=10))

    renewed = await service.change_expiry(ADMIN, invitation.id, clock.now() + timedelta(days=30))

    assert renewed.status is InvitationStatus.ACCEPTED
    assert renewed.revoked_at is None


async def test_pasados_90_dias_no_se_renueva(
    service: InvitationService, uow: FakeIdentityUnitOfWork, clock: FixedClock
) -> None:
    invitation, _ = await accepted(service, uow, days=30)
    clock.advance(timedelta(days=30 + 91))
    invitation.status = InvitationStatus.EXPIRED

    with pytest.raises(InvitationNotRenewableError):
        await service.change_expiry(ADMIN, invitation.id, clock.now() + timedelta(days=30))


async def test_un_invitado_suprimido_no_se_renueva(
    service: InvitationService, uow: FakeIdentityUnitOfWork, clock: FixedClock
) -> None:
    invitation, guest = await accepted(service, uow)
    guest.request_deletion()
    guest.to_tombstone()

    with pytest.raises(GuestErasedError) as info:
        await service.change_expiry(ADMIN, invitation.id, clock.now() + timedelta(days=30))
    assert info.value.slug == "guest-erased"
    assert isinstance(info.value, ConflictError)
