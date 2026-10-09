"""T105: acceso del invitado (FR-007, FR-011; data-model §2.7 y §4.2)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from saber_uli.identity.domain.invitation import (
    AccessExpiryOutOfRangeError,
    GuestAccessExpiredError,
    GuestAccessRevokedError,
    Invitation,
    InvitationNotPendingError,
    InvitationStatus,
)
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.user import UserKind, UserStatus
from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
TEACHER = UUID("00000000-0000-7000-8000-0000000000aa")
GUEST = UUID("00000000-0000-7000-8000-0000000000bb")


def invitation(days: int = 30, **overrides: object) -> Invitation:
    values: dict[str, object] = {
        "email": "laura@correo.co",
        "invited_by": TEACHER,
        "access_expires_at": T0 + timedelta(days=days),
        "now": T0,
    }
    values.update(overrides)
    return Invitation.create(**values)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------- creación


def test_una_invitacion_nueva_queda_enviada() -> None:
    created = invitation(invitee_name="Laura")

    assert created.status is InvitationStatus.SENT
    assert created.sent_at == T0
    assert created.guest_user_id is None
    assert created.invitee_name == "Laura"
    assert created.email == "laura@correo.co"


def test_el_comando_del_sistema_invita_sin_usuario() -> None:
    assert invitation(invited_by=None).invited_by is None


@pytest.mark.parametrize("days", [0, -1])
def test_el_acceso_debe_vencer_en_el_futuro(days: int) -> None:
    with pytest.raises(AccessExpiryOutOfRangeError) as info:
        invitation(days=days)
    assert isinstance(info.value, RuleViolationError)
    assert info.value.slug == "access-expiry-out-of-range"


def test_el_correo_se_guarda_sin_espacios() -> None:
    assert invitation(email="  Laura@Correo.co ").email == "Laura@Correo.co"


# ---------------------------------------------------------------------------- aceptar


def test_el_usuario_del_invitado_solo_tiene_el_rol_invitado() -> None:
    user = invitation(invitee_name="Laura Gómez").new_guest_user(T0)

    assert user.kind is UserKind.GUEST
    assert user.status is UserStatus.ACTIVE
    assert user.roles == {Role.GUEST}
    assert user.email == "laura@correo.co"
    assert user.display_name == "Laura Gómez"


def test_aceptar_pasa_a_accepted_y_enlaza_al_invitado() -> None:
    pending = invitation()
    later = T0 + timedelta(hours=2)

    pending.accept(GUEST, later)

    assert pending.status is InvitationStatus.ACCEPTED
    assert pending.accepted_at == later
    assert pending.guest_user_id == GUEST


def test_no_se_acepta_dos_veces() -> None:
    accepted = invitation()
    accepted.accept(GUEST, T0)

    with pytest.raises(InvitationNotPendingError) as info:
        accepted.accept(GUEST, T0 + timedelta(minutes=1))
    assert isinstance(info.value, ConflictError)


def test_no_se_acepta_si_el_acceso_ya_vencio() -> None:
    pending = invitation(days=1)

    with pytest.raises(GuestAccessExpiredError):
        pending.accept(GUEST, T0 + timedelta(days=1))


def test_no_se_acepta_una_invitacion_revocada() -> None:
    pending = invitation()
    pending.revoke(T0)

    with pytest.raises(GuestAccessRevokedError):
        pending.accept(GUEST, T0 + timedelta(minutes=1))


# ---------------------------------------------------------------------------- vigencia


def test_acceso_vigente_si_aceptada_sin_revocar_y_antes_del_vencimiento() -> None:
    accepted = invitation(days=10)
    accepted.accept(GUEST, T0)

    assert accepted.has_access(T0 + timedelta(days=9, hours=23))
    assert not accepted.has_access(T0 + timedelta(days=10))
    accepted.ensure_access(T0 + timedelta(days=9))  # no lanza


def test_sin_aceptar_no_hay_acceso() -> None:
    assert not invitation().has_access(T0)


def test_el_fin_del_acceso_es_el_minimo_entre_revocacion_y_vencimiento() -> None:
    accepted = invitation(days=10)
    accepted.accept(GUEST, T0)
    assert accepted.access_ends_at == T0 + timedelta(days=10)

    accepted.revoke(T0 + timedelta(days=3))

    assert accepted.access_ends_at == T0 + timedelta(days=3)
    assert accepted.status is InvitationStatus.REVOKED


def test_acceso_vencido_responde_guest_access_expired() -> None:
    accepted = invitation(days=1)
    accepted.accept(GUEST, T0)

    with pytest.raises(GuestAccessExpiredError) as info:
        accepted.ensure_access(T0 + timedelta(days=2))
    assert info.value.slug == "guest-access-expired"


def test_acceso_revocado_responde_guest_access_revoked_aunque_tambien_haya_vencido() -> None:
    accepted = invitation(days=1)
    accepted.accept(GUEST, T0)
    accepted.revoke(T0 + timedelta(hours=1))

    with pytest.raises(GuestAccessRevokedError) as info:
        accepted.ensure_access(T0 + timedelta(days=2))
    assert info.value.slug == "guest-access-revoked"
