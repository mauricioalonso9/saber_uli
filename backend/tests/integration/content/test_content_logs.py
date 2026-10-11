"""T113: los logs del banco de ítems no llevan datos personales ni contenido (principio V).

Captura todos los logs (nivel DEBUG) de la carga del banco inicial con errores, la importación
(con un nombre de archivo único), la autoría, la revisión con comentarios, el retiro con motivo y
la exportación. Al final no aparece ningún texto de ítem, nombre, correo, comentario, motivo ni
nombre de archivo; solo códigos, identificadores y conteos.
"""

import io
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from saber_uli.main import create_app
from tests.integration.conftest import settings_for
from tests.integration.content.conftest import LcTaxonomy
from tests.integration.content.imports import bank_file, lc_context, lc_item
from tests.integration.content.test_cli_load_seed import SEED, run_load
from tests.integration.identity.staff import StaffFactory


async def test_los_logs_del_banco_no_llevan_datos_personales(
    migrated_database: dict[str, str],
    redis_url: str,
    redis_client: Any,
    staff: StaffFactory,
    lc_taxonomy: LcTaxonomy,
    app_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
    mark = uuid4().hex[:8]
    secrets: list[str] = []

    # Carga del banco inicial con un ítem inválido cuyo enunciado es único.
    bank = json.loads(SEED.read_text(encoding="utf-8"))
    bank["items"][0]["enunciado"] = f"Enunciado del banco {mark}"
    bank["items"][0]["afirmacion"] = "LC-A99"
    seed_file = tmp_path / f"banco-de-{mark}.json"
    seed_file.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")
    seed_run = run_load(migrated_database["app"], "--file", str(seed_file))
    assert seed_run.returncode == 1
    seed_output = seed_run.stdout + seed_run.stderr
    secrets += [f"Enunciado del banco {mark}", f"banco-de-{mark}"]

    logs = io.StringIO()
    settings = settings_for(migrated_database, redis_url).model_copy(update={"log_level": "DEBUG"})
    app = create_app(settings, log_stream=logs)
    teacher = await staff(Role.TEACHER)
    admin = await staff(Role.ADMIN)
    name = f"Docente Registro {mark}"
    async with app_engine.begin() as conn:
        await conn.execute(
            text("UPDATE identity.users SET display_name = :n WHERE id = :u"),
            {"n": name, "u": teacher.id},
        )
        email = (
            await conn.execute(
                text("SELECT email FROM identity.users WHERE id = :u"), {"u": teacher.id}
            )
        ).scalar_one()
    secrets += [name, str(email)]

    stem = f"Enunciado secreto {mark}"
    body = f"Texto del contexto {mark}"
    filename = f"importacion-de-{mark}.json"
    comment = f"Comentario secreto {mark}"
    reason = f"Motivo secreto {mark}"
    secrets += [stem, body, filename, comment, reason]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        t, a = teacher.headers, admin.headers
        # Importación: uno válido y uno con error, con textos únicos.
        content = bank_file(
            [
                lc_item(1, enunciado=stem),
                lc_item(2, afirmacion="LC-A9", enunciado=stem + " 2"),
                lc_item(3, enunciado=stem + " 3"),
            ],
            contexts=[lc_context(body=body)],
        )
        created = await client.post(
            "/api/v1/content/imports",
            files={"file": (filename, content, "application/json")},
            headers=t,
        )
        assert created.status_code == 201, created.text
        import_id = created.json()["id"]
        await client.get(f"/api/v1/content/imports/{import_id}/report", headers=t)
        confirmed = await client.post(
            f"/api/v1/content/imports/{import_id}/confirmation",
            json={"target_state": "in_review", "originality_declared": True},
            headers=t,
        )
        assert confirmed.status_code == 200, confirmed.text

        # Revisión: devolver con comentario y rechazar con motivo.
        item = (await client.get("/api/v1/content/items/LC-0001", headers=a)).json()
        returned = await client.post(
            "/api/v1/content/items/LC-0001/return",
            json={"comment": comment},
            headers={**a, "If-Match": f'"{item["revision"]}"'},
        )
        assert returned.status_code == 200, returned.text
        await client.post(
            "/api/v1/content/items/LC-0001/comments", json={"comment": comment}, headers=t
        )
        other = (await client.get("/api/v1/content/items/LC-0003", headers=a)).json()
        rejected = await client.post(
            "/api/v1/content/items/LC-0003/rejection",
            json={"reason": reason},
            headers={**a, "If-Match": f'"{other["revision"]}"'},
        )
        assert rejected.status_code == 200, rejected.text
        # Un error de validación con el texto en el cuerpo.
        await client.post(
            "/api/v1/content/items",
            json={"code": "LC-0099", "module": "LC", "kind": "selection", "stem_md": stem},
            headers=t,
        )

        # Exportación.
        exported = await client.get(
            "/api/v1/content/export", params={"format": "json", "version": "latest"}, headers=t
        )
        assert exported.status_code == 200
        assert stem in exported.text  # el archivo sí lo lleva; los logs no

    captured = seed_output + logs.getvalue()
    assert "http_request" in captured  # hubo logs
    leaked = [secret for secret in secrets if secret in captured]
    assert leaked == []
