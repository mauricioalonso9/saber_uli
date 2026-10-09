"""T123: lotes de invitaciones (FR-009; escenario 5.2; SC-005; data-model §2.9)."""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from saber_uli.identity.domain.invitation_batch import (
    BATCH_MAX_ROWS,
    BatchNotPendingError,
    BatchRowInput,
    BatchStatus,
    BatchTooLargeError,
    InvalidBatchFileError,
    InvitationBatch,
    RowResult,
    parse_csv,
)
from saber_uli.identity.domain.settings import IdentitySettings
from saber_uli.shared.domain.errors import ConflictError

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
TEACHER = uuid4()
DOMAINS = ("unilibre.edu.co",)


def validate(
    rows: list[BatchRowInput],
    *,
    is_admin: bool = False,
    existing: set[str] | None = None,
    default: datetime | None = None,
) -> InvitationBatch:
    return InvitationBatch.validate(
        rows,
        created_by=TEACHER,
        is_admin=is_admin,
        existing_emails=existing or set(),
        institutional_domains=DOMAINS,
        settings=IdentitySettings(),
        now=T0,
        default_access_expires_at=default,
    )


def row(line: int, email: str, **extra: object) -> BatchRowInput:
    return BatchRowInput(line=line, email=email, **extra)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------- CSV


def test_lee_el_csv_con_encabezado_y_fecha_de_vencimiento() -> None:
    rows = parse_csv(
        "﻿correo,nombre,vence\nlaura@correo.co,Laura Gómez,2027-01-31\npedro@correo.co,,\n"
    )

    assert rows[0].line == 2
    assert (rows[0].email, rows[0].name) == ("laura@correo.co", "Laura Gómez")
    # «vence» es una fecha: el acceso dura hasta el final de ese día en Colombia.
    assert rows[0].access_expires_at == datetime(2027, 2, 1, 4, 59, 59, tzinfo=UTC)
    assert (rows[1].line, rows[1].name, rows[1].access_expires_at) == (3, None, None)


@pytest.mark.parametrize(
    "content", ["email,name,expires\nx@y.co,,\n", "", "correo;nombre;vence\nx@y.co;;\n"]
)
def test_un_encabezado_distinto_se_rechaza(content: str) -> None:
    with pytest.raises(InvalidBatchFileError):
        parse_csv(content)


def test_una_fecha_mal_escrita_queda_como_vencimiento_invalido() -> None:
    [parsed] = parse_csv("correo,nombre,vence\nlaura@correo.co,Laura,31/01/2027\n")

    batch = validate([parsed])

    assert batch.rows[0].result is RowResult.EXPIRY_OUT_OF_RANGE


def test_mas_de_500_filas_se_rechaza() -> None:
    content = "correo,nombre,vence\n" + "".join(
        f"p{i}@correo.co,,\n" for i in range(BATCH_MAX_ROWS + 1)
    )

    with pytest.raises(BatchTooLargeError) as info:
        parse_csv(content)
    assert info.value.slug == "batch-too-large"

    with pytest.raises(BatchTooLargeError):
        validate([row(i + 2, f"p{i}@correo.co") for i in range(BATCH_MAX_ROWS + 1)])


# ---------------------------------------------------------------------------- validación


def test_resultado_por_fila() -> None:
    batch = validate(
        [
            row(2, "laura@correo.co", name="Laura"),
            row(3, "no-es-correo"),
            row(4, "LAURA@correo.co"),
            row(5, "ya@correo.co"),
            row(6, "ana@est.unilibre.edu.co"),
            row(7, "lejos@correo.co", access_expires_at=T0 + timedelta(days=181)),
            row(8, "pasado@correo.co", access_expires_at=T0 - timedelta(days=1)),
        ],
        existing={"ya@correo.co"},
    )

    assert [(r.line, r.result) for r in batch.rows] == [
        (2, RowResult.VALID),
        (3, RowResult.INVALID_EMAIL),
        (4, RowResult.DUPLICATE_IN_FILE),
        (5, RowResult.ALREADY_INVITED),
        (6, RowResult.INSTITUTIONAL_EMAIL),
        (7, RowResult.EXPIRY_OUT_OF_RANGE),
        (8, RowResult.EXPIRY_OUT_OF_RANGE),
    ]
    assert (batch.valid_count, batch.invalid_count) == (1, 6)
    assert all(r.message for r in batch.rows if r.result is not RowResult.VALID)
    assert [r.email for r in batch.valid_rows()] == ["laura@correo.co"]


def test_el_administrador_no_tiene_plazo_maximo() -> None:
    batch = validate(
        [row(2, "lejos@correo.co", access_expires_at=T0 + timedelta(days=400))], is_admin=True
    )

    assert batch.rows[0].result is RowResult.VALID


def test_sin_vencimiento_usa_el_del_lote_o_el_plazo_por_defecto() -> None:
    by_default = validate([row(2, "a@correo.co")])
    by_batch = validate([row(2, "a@correo.co")], default=T0 + timedelta(days=20))

    assert by_default.rows[0].access_expires_at == T0 + timedelta(days=90)
    assert by_batch.rows[0].access_expires_at == T0 + timedelta(days=20)


def test_el_lote_queda_pendiente_24_horas() -> None:
    batch = validate([row(2, "a@correo.co")])

    assert batch.status is BatchStatus.PENDING_CONFIRMATION
    assert batch.expires_at == T0 + timedelta(hours=24)
    assert batch.created_by == TEACHER


def test_validar_500_filas_toma_menos_de_2_segundos() -> None:
    rows = [row(i + 2, f"persona{i}@correo.co", name=f"Persona {i}") for i in range(500)]

    started = time.perf_counter()
    batch = validate(rows, existing={f"persona{i}@correo.co" for i in range(0, 500, 7)})

    assert time.perf_counter() - started < 2
    assert batch.valid_count + batch.invalid_count == 500


# ---------------------------------------------------------------------------- confirmar


def test_confirmar_una_sola_vez() -> None:
    batch = validate([row(2, "a@correo.co")])

    batch.confirm(T0 + timedelta(hours=1))

    assert batch.status is BatchStatus.CONFIRMED
    assert batch.confirmed_at == T0 + timedelta(hours=1)
    with pytest.raises(BatchNotPendingError) as info:
        batch.confirm(T0 + timedelta(hours=2))
    assert info.value.slug == "batch-not-pending"
    assert isinstance(info.value, ConflictError)


def test_un_lote_vencido_no_se_confirma() -> None:
    batch = validate([row(2, "a@correo.co")])

    with pytest.raises(BatchNotPendingError):
        batch.confirm(T0 + timedelta(hours=24))
