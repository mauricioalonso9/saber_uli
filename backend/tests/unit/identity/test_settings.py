"""T055: parámetros configurables (research R-29; data-model §2.15; contrato: `Settings`)."""

from datetime import timedelta

import pytest

from saber_uli.identity.domain.settings import (
    SETTING_RANGES,
    IdentitySettings,
    SettingOutOfRangeError,
)
from saber_uli.shared.domain.errors import RuleViolationError


def test_valores_por_defecto() -> None:
    settings = IdentitySettings()

    assert settings.teacher_max_access_days == 180
    assert settings.default_guest_access_days == 90
    assert settings.invitation_link_ttl_days == 7
    assert settings.sign_in_link_ttl_minutes == 10  # ASVS 2.7.2 (T178a)


def test_rangos_del_contrato() -> None:
    assert SETTING_RANGES == {
        "teacher_max_access_days": (1, 730),
        "default_guest_access_days": (1, 730),
        "invitation_link_ttl_days": (1, 30),
        "sign_in_link_ttl_minutes": (5, 10),
    }


@pytest.mark.parametrize(
    ("key", "low", "high"),
    [
        ("teacher_max_access_days", 1, 730),
        ("default_guest_access_days", 1, 730),
        ("invitation_link_ttl_days", 1, 30),
        ("sign_in_link_ttl_minutes", 5, 10),
    ],
)
def test_los_limites_se_aceptan_y_fuera_de_rango_se_rechaza(key: str, low: int, high: int) -> None:
    assert getattr(IdentitySettings().with_changes(**{key: low}), key) == low
    assert getattr(IdentitySettings().with_changes(**{key: high}), key) == high

    for bad in (low - 1, high + 1):
        with pytest.raises(SettingOutOfRangeError) as info:
            IdentitySettings().with_changes(**{key: bad})
        assert isinstance(info.value, RuleViolationError)
        assert info.value.slug == "validation-error"


def test_with_changes_no_modifica_el_original() -> None:
    original = IdentitySettings()
    changed = original.with_changes(sign_in_link_ttl_minutes=8)

    assert original.sign_in_link_ttl_minutes == 10
    assert changed.sign_in_link_ttl_minutes == 8
    assert changed.changed_keys(original) == {"sign_in_link_ttl_minutes"}


def test_clave_desconocida() -> None:
    with pytest.raises(TypeError):
        IdentitySettings().with_changes(otra=1)


def test_duraciones() -> None:
    settings = IdentitySettings()

    assert settings.teacher_max_access == timedelta(days=180)
    assert settings.default_guest_access == timedelta(days=90)
    assert settings.invitation_link_ttl == timedelta(days=7)
    assert settings.sign_in_link_ttl == timedelta(minutes=10)
