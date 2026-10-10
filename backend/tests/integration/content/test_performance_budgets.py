"""T110: presupuestos de rendimiento del banco (SC-003, SC-004, SC-009, SC-010; research R-18).

Siembra 10 000 ítems publicados de LC (marca `carga-002-`) y mide por la API completa, con
PostgreSQL real:

- SC-004: vista previa de un archivo de 500 ítems nuevos (< 30 s);
- SC-003: confirmación de esos 500 (< 60 s);
- SC-009: `listItems` con búsqueda y filtros, cobertura y estadísticas de un ítem (< 2 s);
- SC-010: exportación completa en JSON (< 60 s).

Los tiempos se imprimen siempre y se exigen solo con `PERF_BUDGETS_ENFORCE=1` (en Windows con
Docker Desktop cada viaje a PostgreSQL pasa por la VM; la medición definitiva va en el servidor de
referencia, como en 001/T176).
"""

import json
import os
import time
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import create_async_engine

from saber_uli.identity.domain.roles import Role
from tests.integration.content.conftest import LcTaxonomy
from tests.integration.content.imports import bank_file, lc_item
from tests.integration.identity.staff import StaffFactory

SEEDED_ITEMS = 10_000
IMPORT_ITEMS = 500
SEED_MARK = "carga-002-"
BUDGETS_S = {
    "vista previa de 500 (SC-004)": 30.0,
    "confirmación de 500 (SC-003)": 60.0,
    "listItems con búsqueda y filtros (SC-009)": 2.0,
    "listItems por categoría (SC-009)": 2.0,
    "cobertura de LC (SC-009)": 2.0,
    "estadísticas de un ítem (SC-009)": 2.0,
    "exportación completa (SC-010)": 60.0,
}


@pytest.fixture
async def seeded(migrated_database: dict[str, str], lc_taxonomy: LcTaxonomy) -> AsyncIterator[None]:
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    tags = {
        "competence": lc_taxonomy.competence.id,
        "assertion": lc_taxonomy.assertion.id,
        "other": lc_taxonomy.other_assertion.id,
        "evidence": lc_taxonomy.evidence.id,
    }
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO content.items (code, module_code, kind, origin)
                   SELECT 'LC-' || lpad(g::text, 5, '0'), 'LC', 'selection', 'teacher'
                   FROM generate_series(10001, 10000 + :n) AS g"""
            ),
            {"n": SEEDED_ITEMS},
        )
        await conn.execute(
            text(
                """INSERT INTO content.item_versions
                       (item_id, number, state, difficulty, competence_id, assertion_id,
                        evidence_id, stem_md, options, explanation_md, content_hash, fingerprint,
                        published_at)
                   SELECT i.id, 1, 'published',
                          (ARRAY['low', 'medium', 'high'])[1 + (row_number() OVER () % 3)],
                          CAST(:competence AS uuid),
                          CASE WHEN row_number() OVER () % 2 = 0 THEN CAST(:assertion AS uuid) ELSE CAST(:other AS uuid) END,
                          CASE WHEN row_number() OVER () % 2 = 0 THEN CAST(:evidence AS uuid) END,
                          :mark || i.code || ' ¿Qué sostiene el autor sobre la lectura?',
                          jsonb_build_array(
                              jsonb_build_object('key', 'A', 'text', 'Opción A ' || i.code,
                                                 'correct', true, 'feedback', 'Porque A.'),
                              jsonb_build_object('key', 'B', 'text', 'Opción B ' || i.code,
                                                 'correct', false, 'feedback', 'Porque B.'),
                              jsonb_build_object('key', 'C', 'text', 'Opción C ' || i.code,
                                                 'correct', false, 'feedback', 'Porque C.'),
                              jsonb_build_object('key', 'D', 'text', 'Opción D ' || i.code,
                                                 'correct', false, 'feedback', 'Porque D.')),
                          'Se apoya en el texto.',
                          sha256(convert_to('hash-' || i.code, 'UTF8')),
                          sha256(convert_to('print-' || i.code, 'UTF8')),
                          now()
                   FROM content.items i WHERE length(i.code) = 8"""
            ),
            {**tags, "mark": SEED_MARK},
        )
        await conn.execute(text("ANALYZE content.items, content.item_versions"))
    await engine.dispose()
    yield


async def timed(timings: dict[str, float], name: str, call: object) -> httpx.Response:
    start = time.perf_counter()
    response = await call  # type: ignore[misc]
    timings[name] = time.perf_counter() - start
    assert isinstance(response, httpx.Response)
    assert response.status_code in (200, 201), response.text[:300]
    return response


async def test_presupuestos_del_banco(
    api_client: httpx.AsyncClient,
    staff: StaffFactory,
    lc_taxonomy: LcTaxonomy,
    seeded: None,
) -> None:
    teacher = (await staff(Role.TEACHER)).headers
    timings: dict[str, float] = {}
    items = [
        lc_item(
            n,
            enunciado=f"Pregunta de la carga número {n}: ¿qué propone el texto?",
            opciones=[
                {
                    "clave": key,
                    "texto": f"Opción {key} de la carga {n}",
                    "correcta": key == "A",
                    "retroalimentacion": f"Porque {key}.",
                }
                for key in "ABCD"
            ],
        )
        for n in range(1, IMPORT_ITEMS + 1)
    ]

    preview = await timed(
        timings,
        "vista previa de 500 (SC-004)",
        api_client.post(
            "/api/v1/content/imports",
            files={"file": ("carga.json", bank_file(items), "application/json")},
            headers=teacher,
        ),
    )
    assert preview.json()["counts"]["create"] == IMPORT_ITEMS + 1  # y su contexto
    await timed(
        timings,
        "confirmación de 500 (SC-003)",
        api_client.post(
            f"/api/v1/content/imports/{preview.json()['id']}/confirmation",
            json={"target_state": "draft", "originality_declared": True},
            headers=teacher,
        ),
    )
    listed = await timed(
        timings,
        "listItems con búsqueda y filtros (SC-009)",
        api_client.get(
            "/api/v1/content/items",
            params={"q": "lectura", "module": "LC", "state": "published", "difficulty": "medium"},
            headers=teacher,
        ),
    )
    assert listed.json()["meta"]["total"] > 0
    await timed(
        timings,
        "listItems por categoría (SC-009)",
        api_client.get(
            "/api/v1/content/items",
            params={"taxonomy_node": str(lc_taxonomy.competence.id)},
            headers=teacher,
        ),
    )
    await timed(
        timings,
        "cobertura de LC (SC-009)",
        api_client.get("/api/v1/content/coverage/LC", headers=teacher),
    )
    await timed(
        timings,
        "estadísticas de un ítem (SC-009)",
        api_client.get("/api/v1/content/items/LC-15000/statistics", headers=teacher),
    )
    exported = await timed(
        timings,
        "exportación completa (SC-010)",
        api_client.get("/api/v1/content/export", params={"format": "json"}, headers=teacher),
    )
    assert len(json.loads(exported.content)["items"]) == SEEDED_ITEMS

    print("\nPresupuestos del banco (T110):")
    for name, seconds in timings.items():
        print(f"  {name}: {seconds:.2f} s (meta {BUDGETS_S[name]:.0f} s)")
    if os.environ.get("PERF_BUDGETS_ENFORCE") == "1":
        over = {n: s for n, s in timings.items() if s >= BUDGETS_S[n]}
        assert over == {}, f"fuera de presupuesto: {over}"
