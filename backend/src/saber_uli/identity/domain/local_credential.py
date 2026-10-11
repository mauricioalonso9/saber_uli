"""Credencial de la cuenta local de administración (US9; FR-040 a FR-045; R-41, ADR 0009).

Una sola cuenta, `adminsaber`, ingresa con usuario y contraseña. Nace con la contraseña inicial
`adminsaber` y el cambio obligatorio. El dominio solo ve el hash (lo calcula la infraestructura
con Argon2id) y aplica la política de la contraseña nueva y el bloqueo por fallos seguidos.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from saber_uli.shared.domain.errors import RuleViolationError

LOCAL_ADMIN_USERNAME = "adminsaber"
# Pública a propósito: el primer ingreso obliga a cambiarla (FR-041).
INITIAL_PASSWORD = "adminsaber"  # noqa: S105
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MAX_FAILED_ATTEMPTS = 10
LOCK_MINUTES = 15


class PasswordRule(StrEnum):
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    SAME_AS_USERNAME = "same_as_username"
    SAME_AS_CURRENT = "same_as_current"
    TOO_COMMON = "too_common"


_MESSAGES = {
    PasswordRule.TOO_SHORT: f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.",
    PasswordRule.TOO_LONG: f"La contraseña puede tener hasta {MAX_PASSWORD_LENGTH} caracteres.",
    PasswordRule.SAME_AS_USERNAME: "La contraseña no puede ser igual al usuario.",
    PasswordRule.SAME_AS_CURRENT: "La contraseña nueva debe ser distinta de la actual.",
    PasswordRule.TOO_COMMON: "Esa contraseña es demasiado común; elige otra.",
}


class WeakPasswordError(RuleViolationError):
    slug = "weak-password"

    def __init__(self, rule: PasswordRule) -> None:
        super().__init__(_MESSAGES[rule])
        self.rule = rule


def check_new_password(
    password: str, *, username: str, same_as_current: bool, common: Collection[str]
) -> None:
    """Política de FR-042 (ASVS V2.1): sin reglas de composición ni recortes."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(PasswordRule.TOO_SHORT)
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPasswordError(PasswordRule.TOO_LONG)
    if password.strip().casefold() == username.casefold():
        raise WeakPasswordError(PasswordRule.SAME_AS_USERNAME)
    if same_as_current:
        raise WeakPasswordError(PasswordRule.SAME_AS_CURRENT)
    if password.casefold() in common:
        raise WeakPasswordError(PasswordRule.TOO_COMMON)


@dataclass
class LocalCredential:
    user_id: UUID
    password_hash: str
    must_change: bool
    failed_attempts: int
    locked_until: datetime | None
    changed_at: datetime

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and now < self.locked_until

    def seconds_locked(self, now: datetime) -> int:
        if self.locked_until is None or now >= self.locked_until:
            return 0
        return int((self.locked_until - now).total_seconds())

    def record_failure(self, now: datetime) -> bool:
        """Cuenta un fallo; `True` si este fallo bloquea la cuenta (FR-044)."""
        if self.locked_until is not None and now >= self.locked_until:
            self.failed_attempts, self.locked_until = 0, None
        self.failed_attempts += 1
        if self.failed_attempts >= MAX_FAILED_ATTEMPTS:
            self.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            return True
        return False

    def record_success(self) -> None:
        self.failed_attempts, self.locked_until = 0, None

    def change_password(self, password_hash: str, now: datetime) -> None:
        self.password_hash = password_hash
        self.must_change = False
        self.changed_at = now
        self.record_success()

    def reset(self, initial_hash: str, now: datetime) -> None:
        """Vuelve a la contraseña inicial con el cambio obligatorio (FR-046)."""
        self.password_hash = initial_hash
        self.must_change = True
        self.changed_at = now
        self.record_success()
