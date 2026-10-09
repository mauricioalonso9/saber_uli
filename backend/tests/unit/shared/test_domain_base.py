"""T022: bloques de dominio compartidos (eventos, reloj y errores)."""

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

import pytest

from saber_uli.shared.domain.clock import Clock, FixedClock, SystemClock
from saber_uli.shared.domain.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
    UnauthenticatedError,
)
from saber_uli.shared.domain.events import DomainEvent

NOON = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
BOGOTA = timezone(timedelta(hours=-5))


@dataclass(frozen=True, kw_only=True)
class AlgoOcurrio(DomainEvent):
    event_type: ClassVar[str] = "identity.AlgoOcurrio"
    user_id: UUID


# --- Eventos -------------------------------------------------------------------------------


def test_cada_evento_tiene_un_event_id_propio() -> None:
    uid = UUID(int=1)
    first = AlgoOcurrio(occurred_at=NOON, user_id=uid)
    second = AlgoOcurrio(occurred_at=NOON, user_id=uid)

    assert isinstance(first.event_id, UUID)
    assert first.event_id != second.event_id


def test_el_evento_es_inmutable() -> None:
    event = AlgoOcurrio(occurred_at=NOON, user_id=UUID(int=1))

    with pytest.raises(FrozenInstanceError):
        event.user_id = UUID(int=2)  # type: ignore[misc]


def test_occurred_at_es_obligatorio() -> None:
    with pytest.raises(TypeError):
        AlgoOcurrio(user_id=UUID(int=1))  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "when",
    [datetime(2026, 10, 6, 12, 0), datetime(2026, 10, 6, 7, 0, tzinfo=BOGOTA)],
    ids=["sin-zona", "bogota"],
)
def test_occurred_at_debe_estar_en_utc(when: datetime) -> None:
    with pytest.raises(ValueError):
        AlgoOcurrio(occurred_at=when, user_id=UUID(int=1))


def test_event_type_se_lee_desde_la_clase_y_la_instancia() -> None:
    event = AlgoOcurrio(occurred_at=NOON, user_id=UUID(int=1))

    assert AlgoOcurrio.event_type == "identity.AlgoOcurrio"
    assert event.event_type == "identity.AlgoOcurrio"


def test_una_subclase_sin_event_type_se_rechaza() -> None:
    with pytest.raises(TypeError):

        @dataclass(frozen=True, kw_only=True)
        class SinTipo(DomainEvent):
            pass


@pytest.mark.parametrize("bad", ["AlgoOcurrio", "identity.algo_ocurrio", "Identity.Algo", ""])
def test_un_event_type_mal_formado_se_rechaza(bad: str) -> None:
    with pytest.raises(TypeError):

        @dataclass(frozen=True, kw_only=True)
        class MalNombrado(DomainEvent):
            event_type: ClassVar[str] = bad


# --- Reloj ---------------------------------------------------------------------------------


def usa(clock: Clock) -> datetime:
    return clock.now()


def test_system_clock_devuelve_utc_con_zona() -> None:
    now = usa(SystemClock())

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_fixed_clock_no_cambia_entre_llamadas() -> None:
    clock = FixedClock(NOON)

    assert usa(clock) == NOON
    assert clock.now() == NOON


def test_fixed_clock_avanza_y_se_fija() -> None:
    clock = FixedClock(NOON)

    clock.advance(timedelta(minutes=31))
    assert clock.now() == NOON + timedelta(minutes=31)

    later = datetime(2026, 12, 1, tzinfo=UTC)
    clock.set(later)
    assert clock.now() == later


def test_fixed_clock_rechaza_fechas_sin_zona() -> None:
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 10, 6, 12, 0))
    clock = FixedClock(NOON)
    with pytest.raises(ValueError):
        clock.set(datetime(2026, 10, 6, 12, 0))


def test_fixed_clock_normaliza_a_utc() -> None:
    clock = FixedClock(datetime(2026, 10, 6, 7, 0, tzinfo=BOGOTA))

    assert clock.now() == NOON
    assert clock.now().utcoffset() == timedelta(0)
    assert clock.now().tzinfo is UTC


def test_fixture_fixed_clock(fixed_clock: FixedClock) -> None:
    assert fixed_clock.now() == NOON


# --- Errores -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("category", "slug"),
    [
        (UnauthenticatedError, "unauthenticated"),
        (NotFoundError, "not-found"),
        (PermissionDeniedError, "forbidden"),
        (ConflictError, "conflict"),
        (RuleViolationError, "validation-error"),
    ],
)
def test_slug_por_defecto_de_cada_categoria(category: type[DomainError], slug: str) -> None:
    error = category("Mensaje.")

    assert error.slug == slug
    assert isinstance(error, DomainError)


def test_una_subclase_hereda_la_categoria_y_usa_su_slug() -> None:
    class UltimoAdmin(ConflictError):
        slug = "last-admin"

    error = UltimoAdmin("No puedes quitar el rol al último administrador.")

    assert isinstance(error, ConflictError)
    assert error.slug == "last-admin"
    assert error.message == "No puedes quitar el rol al último administrador."
    assert str(error) == error.message


@pytest.mark.parametrize("bad", ["LastAdmin", "last_admin", "last--admin", "-last", ""])
def test_un_slug_mal_formado_se_rechaza(bad: str) -> None:
    with pytest.raises(TypeError):

        class MalSlug(ConflictError):
            slug = bad


def test_domain_error_no_se_instancia_directamente() -> None:
    with pytest.raises(TypeError):
        DomainError("x")
