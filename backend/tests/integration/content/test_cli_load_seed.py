"""T037: `saber-uli content load-seed [--file RUTA]` (US1; FR-021, FR-023; research R-07).

Termina con 0 y deja el log `content_seed_loaded` con conteos; con un archivo inválido termina con
1 y el log `content_seed_failed` trae solo el código de cada elemento y la regla. Ningún log lleva
textos de ítems ni rutas de archivo (principio V).
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SEED = Path(__file__).parents[3] / "seeds" / "banco_inicial_saber_uli.json"


def run_load(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["DATABASE_URL"] = url
    return subprocess.run(  # noqa: S603 - los argumentos los fija la propia prueba
        [sys.executable, "-m", "saber_uli.cli", "content", "load-seed", *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=300,
    )


def events(output: str) -> list[dict[str, Any]]:
    found = []
    for line in output.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and "event" in entry:
            found.append(entry)
    return found


def test_carga_el_banco_y_registra_conteos_sin_datos_del_contenido(
    migrated_database: dict[str, str], tmp_path: Path
) -> None:
    copy = tmp_path / "banco-secreto.json"
    copy.write_bytes(SEED.read_bytes())

    result = run_load(migrated_database["app"], "--file", str(copy))

    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    [loaded] = [e for e in events(output) if e["event"] == "content_seed_loaded"]
    assert loaded["added_items"] == 46
    assert loaded["unchanged_items"] == 0
    assert loaded["pending_manual"] == 0
    assert "banco-secreto" not in output
    assert "Desconectar para aprender" not in output  # título de un contexto del banco

    again = run_load(migrated_database["app"], "--file", str(copy))
    [reloaded] = [
        e for e in events(again.stdout + again.stderr) if e["event"] == "content_seed_loaded"
    ]
    assert (reloaded["added_items"], reloaded["unchanged_items"]) == (0, 46)


def test_un_archivo_invalido_termina_con_1_y_solo_informa_codigos_y_reglas(
    migrated_database: dict[str, str], tmp_path: Path
) -> None:
    bank = json.loads(SEED.read_text(encoding="utf-8"))
    broken = next(i for i in bank["items"] if i["id"] == "LC-0004")
    for option in broken["opciones"]:
        option["correcta"] = True
    path = tmp_path / "invalido.json"
    path.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")

    result = run_load(migrated_database["app"], "--file", str(path))

    assert result.returncode == 1
    output = result.stdout + result.stderr
    [failed] = [e for e in events(output) if e["event"] == "content_seed_failed"]
    assert {"item": "LC-0004", "rule": "single_correct_option"} in failed["problems"]
    assert broken["enunciado"] not in output
    assert "invalido.json" not in output


def test_sin_archivo_usa_el_banco_del_proyecto(migrated_database: dict[str, str]) -> None:
    result = run_load(migrated_database["app"])

    assert result.returncode == 0, result.stderr
    assert any(e["event"] == "content_seed_loaded" for e in events(result.stdout + result.stderr))


def test_un_archivo_que_no_existe_es_un_error_de_uso(
    migrated_database: dict[str, str], tmp_path: Path
) -> None:
    result = run_load(migrated_database["app"], "--file", str(tmp_path / "no-existe.json"))

    assert result.returncode == 2
