"""T095: perfil del primer ingreso y su edición (FR-019 a FR-021; data-model §2.2)."""

from datetime import date
from uuid import UUID

import pytest

from saber_uli.identity.domain.profile import (
    DailyGoal,
    InvalidProfileError,
    Profile,
    ProfileData,
    ProgramNotAvailableError,
    ProgramRef,
)
from saber_uli.identity.domain.user import UserKind
from saber_uli.shared.domain.errors import RuleViolationError

USER = UUID("00000000-0000-7000-8000-000000000001")
PROGRAM = ProgramRef(id=UUID("00000000-0000-7000-8000-0000000000b1"), active=True)
OTHER = ProgramRef(id=UUID("00000000-0000-7000-8000-0000000000b2"), active=True)
EXAM = date(2027, 5, 30)


def institutional_data(**overrides: object) -> ProfileData:
    values: dict[str, object] = {
        "program_id": PROGRAM.id,
        "semester": 8,
        "expected_exam_date": EXAM,
        "daily_goal": DailyGoal.REGULAR,
    }
    values.update(overrides)
    return ProfileData(**values)  # type: ignore[arg-type]


def guest_data(**overrides: object) -> ProfileData:
    values: dict[str, object] = {
        "guest_display_name": "Laura Gómez",
        "daily_goal": DailyGoal.CASUAL,
    }
    values.update(overrides)
    return ProfileData(**values)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------- institucional


def test_un_perfil_nuevo_no_esta_completo() -> None:
    profile = Profile(user_id=USER)

    assert not profile.is_complete(UserKind.INSTITUTIONAL)
    assert not profile.is_complete(UserKind.GUEST)


def test_institucional_completo_con_programa_semestre_fecha_y_meta() -> None:
    profile = Profile(user_id=USER)

    profile.update(UserKind.INSTITUTIONAL, institutional_data(), program=PROGRAM)

    assert profile.is_complete(UserKind.INSTITUTIONAL)
    assert (profile.program_id, profile.semester) == (PROGRAM.id, 8)
    assert profile.expected_exam_date == EXAM
    assert profile.daily_goal is DailyGoal.REGULAR
    assert profile.guest_display_name is None


@pytest.mark.parametrize("missing", ["program_id", "semester", "expected_exam_date"])
def test_institucional_exige_cada_campo(missing: str) -> None:
    with pytest.raises(InvalidProfileError) as info:
        Profile(user_id=USER).update(
            UserKind.INSTITUTIONAL,
            institutional_data(**{missing: None}),
            program=PROGRAM if missing != "program_id" else None,
        )
    assert isinstance(info.value, RuleViolationError)


@pytest.mark.parametrize("semester", [0, 13, -1])
def test_el_semestre_va_de_1_a_12(semester: int) -> None:
    with pytest.raises(InvalidProfileError):
        Profile(user_id=USER).update(
            UserKind.INSTITUTIONAL, institutional_data(semester=semester), program=PROGRAM
        )


@pytest.mark.parametrize("semester", [1, 12])
def test_limites_del_semestre(semester: int) -> None:
    profile = Profile(user_id=USER)

    profile.update(UserKind.INSTITUTIONAL, institutional_data(semester=semester), program=PROGRAM)

    assert profile.semester == semester


def test_institucional_no_indica_nombre_de_invitado() -> None:
    with pytest.raises(InvalidProfileError):
        Profile(user_id=USER).update(
            UserKind.INSTITUTIONAL,
            institutional_data(guest_display_name="Otro nombre"),
            program=PROGRAM,
        )


def test_un_programa_inexistente_se_rechaza() -> None:
    with pytest.raises(ProgramNotAvailableError) as info:
        Profile(user_id=USER).update(UserKind.INSTITUTIONAL, institutional_data(), program=None)
    assert isinstance(info.value, RuleViolationError)


def test_un_programa_inactivo_se_rechaza() -> None:
    inactive = ProgramRef(id=PROGRAM.id, active=False)

    with pytest.raises(ProgramNotAvailableError):
        Profile(user_id=USER).update(UserKind.INSTITUTIONAL, institutional_data(), program=inactive)


def test_conservar_el_programa_actual_aunque_ya_este_inactivo() -> None:
    # Desactivar un programa no impide que sus estudiantes editen el resto del perfil.
    profile = Profile(user_id=USER)
    profile.update(UserKind.INSTITUTIONAL, institutional_data(), program=PROGRAM)
    inactive = ProgramRef(id=PROGRAM.id, active=False)

    profile.update(UserKind.INSTITUTIONAL, institutional_data(semester=9), program=inactive)

    assert profile.semester == 9


def test_cambiar_a_otro_programa_inactivo_se_rechaza() -> None:
    profile = Profile(user_id=USER)
    profile.update(UserKind.INSTITUTIONAL, institutional_data(), program=PROGRAM)

    with pytest.raises(ProgramNotAvailableError):
        profile.update(
            UserKind.INSTITUTIONAL,
            institutional_data(program_id=OTHER.id),
            program=ProgramRef(id=OTHER.id, active=False),
        )


# ---------------------------------------------------------------------------- invitado


def test_invitado_completo_con_nombre_y_meta_sin_fecha() -> None:
    profile = Profile(user_id=USER)

    profile.update(UserKind.GUEST, guest_data(guest_display_name="  Laura Gómez "), program=None)

    assert profile.is_complete(UserKind.GUEST)
    assert profile.guest_display_name == "Laura Gómez"
    assert profile.daily_goal is DailyGoal.CASUAL
    assert profile.expected_exam_date is None


def test_invitado_puede_indicar_la_fecha() -> None:
    profile = Profile(user_id=USER)

    profile.update(UserKind.GUEST, guest_data(expected_exam_date=EXAM), program=None)

    assert profile.expected_exam_date == EXAM


@pytest.mark.parametrize("name", [None, "", " L ", "L" * 121])
def test_el_nombre_del_invitado_tiene_de_2_a_120_caracteres(name: str | None) -> None:
    with pytest.raises(InvalidProfileError):
        Profile(user_id=USER).update(
            UserKind.GUEST, guest_data(guest_display_name=name), program=None
        )


@pytest.mark.parametrize("length", [2, 120])
def test_limites_del_nombre_del_invitado(length: int) -> None:
    profile = Profile(user_id=USER)

    profile.update(UserKind.GUEST, guest_data(guest_display_name="L" * length), program=None)

    assert profile.guest_display_name == "L" * length


@pytest.mark.parametrize(
    "extra", [{"program_id": PROGRAM.id}, {"semester": 3}], ids=["programa", "semestre"]
)
def test_invitado_no_acepta_programa_ni_semestre(extra: dict[str, object]) -> None:
    with pytest.raises(InvalidProfileError):
        Profile(user_id=USER).update(UserKind.GUEST, guest_data(**extra), program=PROGRAM)


def test_la_meta_diaria_solo_admite_casual_regular_o_intensa() -> None:
    assert {goal.value for goal in DailyGoal} == {"casual", "regular", "intense"}
    with pytest.raises(ValueError):
        DailyGoal("extrema")
