"""T098: `saber-uli identity import-programs --csv <archivo>` (data-model §2.5; contrato
`ProgramInput`).

CSV UTF-8 con encabezado `codigo,nombre,seccional`. Inserta o actualiza por código sin duplicar,
reporta las filas inválidas sin abortar las válidas y audita con actor `system` (sin `actor_id`).
"""

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

HEADER = "codigo,nombre,seccional\n"

Programs = Callable[[], Awaitable[dict[str, tuple[str, str, bool]]]]


def run_import(
    url: str | None, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    if url is not None:
        env["DATABASE_URL"] = url
    return subprocess.run(  # noqa: S603 - los argumentos los fija la propia prueba
        [sys.executable, "-m", "saber_uli.cli", "identity", "import-programs", *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
        cwd=cwd,
    )


@pytest.fixture
def prefix() -> str:
    """Prefijo de códigos propio de la prueba (los programas de otras pruebas no interfieren)."""
    return f"T{uuid4().hex[:6].upper()}"


@pytest.fixture
async def programs(migrated_database: dict[str, str], prefix: str) -> AsyncIterator[Programs]:
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)

    async def rows() -> dict[str, tuple[str, str, bool]]:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT code, name, campus, active FROM identity.programs"
                    " WHERE code LIKE :p ORDER BY code"
                ),
                {"p": f"{prefix}%"},
            )
            return {r.code: (r.name, r.campus, r.active) for r in result}

    yield rows
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """DELETE FROM identity.audit_events WHERE target_type = 'program' AND target_id IN
                   (SELECT id FROM identity.programs WHERE code LIKE :p)"""
            ),
            {"p": f"{prefix}%"},
        )
        await conn.execute(
            text("DELETE FROM identity.programs WHERE code LIKE :p"), {"p": f"{prefix}%"}
        )
    await engine.dispose()


async def audit(url: str, prefix: str) -> list[tuple[str, object, object]]:
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """SELECT a.action, a.actor_id, a.details FROM identity.audit_events a
                   JOIN identity.programs p ON p.id = a.target_id
                   WHERE a.target_type = 'program' AND p.code LIKE :p
                   ORDER BY a.occurred_at, a.id"""
            ),
            {"p": f"{prefix}%"},
        )
        rows = [(r.action, r.actor_id, r.details) for r in result]
    await engine.dispose()
    return rows


def write_csv(tmp_path: Path, body: str, *, bom: bool = False) -> Path:
    path = tmp_path / "programas.csv"
    path.write_text(("﻿" if bom else "") + body, encoding="utf-8", newline="")
    return path


async def test_importa_programas_nuevos_y_los_audita(
    migrated_database: dict[str, str], programs: Programs, prefix: str, tmp_path: Path
) -> None:
    csv = write_csv(
        tmp_path,
        HEADER + f"{prefix}-DER,Derecho,Bogotá\n{prefix}-CON,Contaduría Pública,Cali\n",
        bom=True,  # Excel guarda CSV UTF-8 con BOM
    )

    result = run_import(migrated_database["app"], "--csv", str(csv))

    assert result.returncode == 0, result.stderr
    assert "creados: 2" in result.stdout.lower()
    assert await programs() == {
        f"{prefix}-CON": ("Contaduría Pública", "Cali", True),
        f"{prefix}-DER": ("Derecho", "Bogotá", True),
    }
    entries = await audit(migrated_database["migrator"], prefix)
    assert [action for action, _, _ in entries] == ["program.created", "program.created"]
    assert all(actor is None for _, actor, _ in entries)


async def test_repetir_la_carga_no_duplica_y_actualiza_por_codigo(
    migrated_database: dict[str, str], programs: Programs, prefix: str, tmp_path: Path
) -> None:
    url = migrated_database["app"]
    first = write_csv(
        tmp_path, HEADER + f"{prefix}-DER,Derecho,Bogotá\n{prefix}-ING,Ingeniería,Cúcuta\n"
    )
    assert run_import(url, "--csv", str(first)).returncode == 0

    second = write_csv(
        tmp_path,
        HEADER + f"{prefix}-DER,Derecho,Bogotá\n{prefix}-ING,Ingeniería de Sistemas,Cúcuta\n",
    )
    result = run_import(url, "--csv", str(second))

    assert result.returncode == 0, result.stderr
    output = result.stdout.lower()
    assert "creados: 0" in output
    assert "actualizados: 1" in output
    assert "sin cambios: 1" in output
    assert await programs() == {
        f"{prefix}-DER": ("Derecho", "Bogotá", True),
        f"{prefix}-ING": ("Ingeniería de Sistemas", "Cúcuta", True),
    }
    actions = [action for action, _, _ in await audit(migrated_database["migrator"], prefix)]
    assert actions.count("program.updated") == 1


async def test_las_filas_invalidas_se_reportan_sin_abortar_las_validas(
    migrated_database: dict[str, str], programs: Programs, prefix: str, tmp_path: Path
) -> None:
    csv = write_csv(
        tmp_path,
        HEADER
        + f"{prefix}-DER,Derecho,Bogotá\n"  # fila 2: válida
        + f"{prefix.lower()}-x,Minúsculas,Bogotá\n"  # fila 3: código inválido
        + f"{prefix}-AB,Ab,Bogotá\n"  # fila 4: nombre corto
        + f"{prefix}-CD,Contaduría,B\n"  # fila 5: seccional corta
        + f"{prefix}-DER,Derecho repetido,Cali\n"  # fila 6: código repetido en el archivo
        + f"{prefix}-EF,Faltan columnas\n",  # fila 7: columnas incompletas
    )

    result = run_import(migrated_database["app"], "--csv", str(csv))

    assert result.returncode == 1
    report = result.stdout + result.stderr
    for row in (3, 4, 5, 6, 7):
        assert f"fila {row}" in report.lower()
    assert "fila 2" not in report.lower()
    assert "inválidas: 5" in result.stdout.lower()
    assert await programs() == {f"{prefix}-DER": ("Derecho", "Bogotá", True)}


async def test_un_encabezado_distinto_no_importa_nada(
    migrated_database: dict[str, str], programs: Programs, prefix: str, tmp_path: Path
) -> None:
    csv = write_csv(tmp_path, f"code,name,campus\n{prefix}-DER,Derecho,Bogotá\n")

    result = run_import(migrated_database["app"], "--csv", str(csv))

    assert result.returncode == 2
    assert "codigo,nombre,seccional" in result.stderr
    assert await programs() == {}


def test_sin_archivo_o_sin_base_de_datos_es_un_error_de_uso(
    migrated_database: dict[str, str], tmp_path: Path
) -> None:
    url = migrated_database["app"]
    missing = run_import(url, "--csv", str(tmp_path / "no-existe.csv"))
    assert missing.returncode == 2
    assert "no-existe.csv" in missing.stderr

    csv = write_csv(tmp_path, HEADER)
    no_url = run_import(None, "--csv", str(csv))
    assert no_url.returncode == 2
    assert "DATABASE_URL" in no_url.stderr


def test_los_mensajes_no_muestran_la_contrasena(
    migrated_database: dict[str, str], tmp_path: Path
) -> None:
    url = migrated_database["app"]
    bad = make_url(url).set(database="no_existe").render_as_string(hide_password=False)
    csv = write_csv(tmp_path, HEADER + "XX-1,Derecho,Bogotá\n")

    result = run_import(bad, "--csv", str(csv))

    assert result.returncode == 1
    secret = make_url(url).password
    assert secret and secret not in result.stdout + result.stderr
