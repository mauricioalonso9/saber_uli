"""Parámetros configurables del contexto (research R-29; data-model §2.15; FR-006a).

Los rangos son los del esquema `Settings` del contrato. Cada cambio se audita
(`setting.changed`, T139).
"""

from dataclasses import dataclass, fields, replace
from datetime import timedelta
from typing import Any

from saber_uli.shared.domain.errors import RuleViolationError

SETTING_RANGES: dict[str, tuple[int, int]] = {
    "teacher_max_access_days": (1, 730),
    "default_guest_access_days": (1, 730),
    "invitation_link_ttl_days": (1, 30),
    "sign_in_link_ttl_minutes": (5, 60),
}


class SettingOutOfRangeError(RuleViolationError):
    """Valor fuera del rango permitido (422 `validation-error`)."""


@dataclass(frozen=True)
class IdentitySettings:
    teacher_max_access_days: int = 180
    default_guest_access_days: int = 90
    invitation_link_ttl_days: int = 7
    sign_in_link_ttl_minutes: int = 15

    def __post_init__(self) -> None:
        for key, (low, high) in SETTING_RANGES.items():
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise SettingOutOfRangeError(f"{key} debe estar entre {low} y {high}.")

    def with_changes(self, **changes: Any) -> "IdentitySettings":
        return replace(self, **changes)

    def changed_keys(self, previous: "IdentitySettings") -> set[str]:
        return {f.name for f in fields(self) if getattr(self, f.name) != getattr(previous, f.name)}

    def as_dict(self) -> dict[str, int]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @property
    def teacher_max_access(self) -> timedelta:
        return timedelta(days=self.teacher_max_access_days)

    @property
    def default_guest_access(self) -> timedelta:
        return timedelta(days=self.default_guest_access_days)

    @property
    def invitation_link_ttl(self) -> timedelta:
        return timedelta(days=self.invitation_link_ttl_days)

    @property
    def sign_in_link_ttl(self) -> timedelta:
        return timedelta(minutes=self.sign_in_link_ttl_minutes)
