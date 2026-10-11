"""T181: credencial de la cuenta local de administración (US9; FR-041, FR-042, FR-044; R-41)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from saber_uli.identity.domain.local_credential import (
    LOCK_MINUTES,
    MAX_FAILED_ATTEMPTS,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    LocalCredential,
    PasswordRule,
    WeakPasswordError,
    check_new_password,
)

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
COMMON = frozenset({"password1234", "contraseña123", "unilibre2026!"})


def credential(**overrides: object) -> LocalCredential:
    values: dict[str, object] = {
        "user_id": uuid4(),
        "password_hash": "$argon2id$hash",
        "must_change": True,
        "failed_attempts": 0,
        "locked_until": None,
        "changed_at": NOW,
    }
    values.update(overrides)
    return LocalCredential(**values)  # type: ignore[arg-type]


def rule_of(password: str, *, same_as_current: bool = False) -> PasswordRule | None:
    try:
        check_new_password(
            password, username="adminsaber", same_as_current=same_as_current, common=COMMON
        )
    except WeakPasswordError as error:
        return error.rule
    return None


def test_los_limites_de_la_politica() -> None:
    assert (MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH) == (12, 128)
    assert (MAX_FAILED_ATTEMPTS, LOCK_MINUTES) == (10, 15)


@pytest.mark.parametrize(
    ("password", "rule"),
    [
        ("corta123", PasswordRule.TOO_SHORT),
        ("x" * 129, PasswordRule.TOO_LONG),
        ("adminsaber", PasswordRule.TOO_SHORT),
        ("AdminSaber", PasswordRule.TOO_SHORT),
        ("ADMINSABER  ", PasswordRule.SAME_AS_USERNAME),
        ("Password1234", PasswordRule.TOO_COMMON),
        ("CONTRASEÑA123", PasswordRule.TOO_COMMON),
        ("frase larga y propia de 2026", None),
        ("ñandú sobre el puente", None),
        ("x" * 128, None),
    ],
)
def test_la_politica_de_la_contrasena_nueva(password: str, rule: PasswordRule | None) -> None:
    assert rule_of(password) == rule


def test_no_puede_repetir_la_actual() -> None:
    assert rule_of("frase larga y propia de 2026", same_as_current=True) is (
        PasswordRule.SAME_AS_CURRENT
    )


def test_el_mensaje_explica_la_regla() -> None:
    with pytest.raises(WeakPasswordError) as raised:
        check_new_password("corta", username="adminsaber", same_as_current=False, common=COMMON)

    assert "12" in raised.value.message
    assert raised.value.slug == "weak-password"


def test_diez_fallos_seguidos_bloquean_15_minutos() -> None:
    value = credential()

    locked = [value.record_failure(NOW) for _ in range(MAX_FAILED_ATTEMPTS)]

    assert locked == [False] * 9 + [True]
    assert value.is_locked(NOW + timedelta(minutes=14, seconds=59))
    assert not value.is_locked(NOW + timedelta(minutes=15))
    assert value.seconds_locked(NOW + timedelta(minutes=10)) == 300


def test_acertar_reinicia_los_fallos() -> None:
    value = credential(failed_attempts=7)

    value.record_success()

    assert value.failed_attempts == 0
    assert value.locked_until is None


def test_tras_el_bloqueo_se_cuenta_de_nuevo() -> None:
    value = credential(failed_attempts=10, locked_until=NOW)

    assert value.record_failure(NOW + timedelta(minutes=1)) is False
    assert value.failed_attempts == 1


def test_cambiar_y_restablecer() -> None:
    value = credential(must_change=True, failed_attempts=3)

    value.change_password("$argon2id$nuevo", NOW)

    assert (value.password_hash, value.must_change, value.changed_at) == (
        "$argon2id$nuevo",
        False,
        NOW,
    )
    later = NOW + timedelta(days=1)
    value.record_failure(later)
    value.reset("$argon2id$inicial", later)
    assert (value.must_change, value.failed_attempts, value.locked_until) == (True, 0, None)
