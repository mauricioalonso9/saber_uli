"""T106: enlaces de acceso de invitados (FR-007, FR-013; research R-18, R-19; data-model §2.8)."""

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from saber_uli.identity.domain.access_link import (
    AccessLink,
    AccessLinkInvalidError,
    LinkPurpose,
    supersede_unused,
)
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.identity.infrastructure.link_tokens import hash_link_token, new_link_token

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
INVITATION = UUID("00000000-0000-7000-8000-0000000000c1")
DEFAULTS = IdentitySettings()


# ---------------------------------------------------------------------------- tokens


def test_el_token_tiene_256_bits_aleatorios_y_cabe_en_el_contrato() -> None:
    plaintext, token_hash = new_link_token()

    raw = base64.urlsafe_b64decode(plaintext + "=" * (-len(plaintext) % 4))
    assert len(raw) == 32
    assert 32 <= len(plaintext) <= 128  # `token` del contrato (createGuestSession)
    assert plaintext.isascii() and "=" not in plaintext
    assert token_hash == hashlib.sha256(plaintext.encode()).digest()
    assert new_link_token()[0] != plaintext


def test_solo_se_guarda_el_hash() -> None:
    plaintext, token_hash = new_link_token()

    assert hash_link_token(plaintext) == token_hash
    assert len(token_hash) == 32
    assert plaintext.encode() not in token_hash


# ---------------------------------------------------------------------------- vigencias


def link(purpose: LinkPurpose = LinkPurpose.INVITATION, **settings: int) -> AccessLink:
    return AccessLink.issue(
        INVITATION,
        purpose,
        token_hash=b"\x01" * 32,
        now=T0,
        settings=DEFAULTS.with_changes(**settings),
    )


def test_el_enlace_de_invitacion_dura_7_dias_por_defecto() -> None:
    issued = link(LinkPurpose.INVITATION)

    assert issued.expires_at == T0 + timedelta(days=7)
    assert issued.used_at is None
    assert issued.invitation_id == INVITATION


def test_el_enlace_de_ingreso_dura_15_minutos_por_defecto() -> None:
    assert link(LinkPurpose.SIGN_IN).expires_at == T0 + timedelta(minutes=15)


def test_las_vigencias_salen_de_los_parametros() -> None:
    assert link(LinkPurpose.INVITATION, invitation_link_ttl_days=3).expires_at == T0 + timedelta(
        days=3
    )
    assert link(LinkPurpose.SIGN_IN, sign_in_link_ttl_minutes=30).expires_at == T0 + timedelta(
        minutes=30
    )


# ---------------------------------------------------------------------------- un solo uso


def test_consumir_marca_el_uso() -> None:
    issued = link()

    issued.consume(T0 + timedelta(minutes=1))

    assert issued.used_at == T0 + timedelta(minutes=1)


def test_un_enlace_usado_no_sirve_de_nuevo() -> None:
    issued = link()
    issued.consume(T0)

    with pytest.raises(AccessLinkInvalidError) as info:
        issued.consume(T0 + timedelta(seconds=1))
    assert info.value.slug == "access-link-invalid"


@pytest.mark.parametrize("after", [timedelta(minutes=15), timedelta(hours=1)])
def test_un_enlace_vencido_no_sirve(after: timedelta) -> None:
    issued = link(LinkPurpose.SIGN_IN)

    with pytest.raises(AccessLinkInvalidError):
        issued.consume(T0 + after)
    assert issued.used_at is None


def test_emitir_uno_nuevo_invalida_los_anteriores_sin_usar_del_mismo_proposito() -> None:
    old_sign_in = link(LinkPurpose.SIGN_IN)
    used_sign_in = link(LinkPurpose.SIGN_IN)
    used_sign_in.consume(T0)
    invitation_link = link(LinkPurpose.INVITATION)
    later = T0 + timedelta(minutes=5)

    superseded = supersede_unused(
        [old_sign_in, used_sign_in, invitation_link], LinkPurpose.SIGN_IN, later
    )

    assert superseded == [old_sign_in]
    assert old_sign_in.used_at == later
    assert used_sign_in.used_at == T0  # ya usado: no cambia
    assert invitation_link.used_at is None  # otro propósito
    with pytest.raises(AccessLinkInvalidError):
        old_sign_in.consume(later)
